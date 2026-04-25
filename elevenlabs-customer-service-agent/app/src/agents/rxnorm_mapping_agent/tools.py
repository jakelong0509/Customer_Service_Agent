"""
Tools for RxNorm Mapping Skill

Maps medication entities to RxNorm codes (SCD/SBD) with NDC codes.
Uses parameterized queries to prevent SQL injection.
"""
from langchain.tools import tool
from typing import Annotated, List, Dict, Any, Callable
from langchain_core.tools import InjectedToolCallId
from langchain.tools import InjectedState, InjectedStore
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from pydantic import BaseModel
from src.services.RAG_service import RAGService
from src.services.db_service import DBService
from src.infrastructure.milvus import get_milvus
from src.agents.rxnorm_mapping_agent.state import MappingResult, MappingResults, NormalizedText, ExtractedEntities
from langchain_huggingface import HuggingFaceEmbeddings

_embedding_model = HuggingFaceEmbeddings(model_name="neuml/pubmedbert-base-embeddings")
_rag_service = RAGService(embedding_model=_embedding_model)
_db_service = DBService()

# Namespace for long-term memory (LangGraph store API). Groups all abbreviation entries.

_ABBREVIATIONS_NAMESPACE = ("rxnorm_mapping_agent", "abbreviations")

_ALLOWED_TABLES = {
    "rxnorm_relationships",
    "rxnorm_attributes",
    "rxnorm_semantic_types",
    "rxnorm_documentation",
}

_ALLOWED_COLUMNS = {
    "rxnorm_relationships": {"rxcui1", "rxcui2", "rela", "rui", "stype1", "stype2", "dir"},
    "rxnorm_attributes": {"rxcui", "atn", "atv", "styp", "sab", "code"},
    "rxnorm_semantic_types": {"rxcui", "tui", "sty", "stn", "stf"},
    "rxnorm_documentation": {"rxcui", "key", "value"},
}


def _validate_filter(metadata_filter: Dict[str, Any], table: str) -> tuple[list[str], list[Any]]:
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Invalid table: {table}")
    allowed = _ALLOWED_COLUMNS.get(table, set())
    conditions = []
    values = []
    for key, value in metadata_filter.items():
        col = key.lower()
        if col not in allowed:
            raise ValueError(f"Invalid column '{col}' for table '{table}'. Allowed: {allowed}")
        conditions.append(f"{col} = ${len(values) + 1}")
        values.append(value)
    return conditions, values


def _dict_to_milvus_filter(metadata_filter: Dict[str, Any] | None) -> str | None:
    if not metadata_filter:
        return None
    clauses = [
        f"{key.lower()} == '{value}'" if isinstance(value, str) else f"{key.lower()} == {value}"
        for key, value in metadata_filter.items()
    ]
    return " and ".join(clauses)

def _norm(s: str) -> str:
  return (s or "").strip()

# ------------- TEXT NORMALIZE TOOLS --------------
@tool
def store_abbreviations(
  abbr_acr: str,
  use_context: str,
  meaning: str,
  store: Annotated[Any, InjectedStore],
):
  """
  Store MEDIUM and LOW confident clinical abbreviations and acronyms from medical notes
  in long-term memory (namespace-based store).

  Parameters:
  abbr_acr: the clinical abbreviation or acronym written in the medical note
  use_context: the context of the abbreviation or acronym used in the medical note
  meaning: the true meaning of the abbreviation and/or acronym
  """
  try:
    key, val, use_context = _norm(abbr_acr), _norm(meaning), _norm(use_context)
    if not key or not val:
      return "Fail to store: abbreviation and meaning must be non-empty."
    if not use_context:
      return "Fail to store: use_context must be non-empty."
    # LangGraph long-term memory: put(namespace, key, value)
    if hasattr(store, "put"):
      store.put(_ABBREVIATIONS_NAMESPACE, key, {"meaning": val, "use_context": use_context})
      return f"Stored: '{key}' -> '{val}'"
    # Fallback: langchain_core flat store (mset)
    if hasattr(store, "mset"):
      composite_key = f"{_ABBREVIATIONS_NAMESPACE[0]}::{key}"
      store.mset([(composite_key, {"meaning": val, "use_context": use_context})])
      return f"Stored: '{key}' -> '{val}'"
    store[key] = {"meaning": val, "use_context": use_context  }
    return f"Stored: '{key}' -> '{val}'"
  except Exception as e:
    return f"Fail to store abbreviations due to error: {e}"


@tool
def retrieve_abbreviations(
  abbr_acr: str,
  store: Annotated[Any, InjectedStore],
):
  """
  Retrieve the meaning of a clinical abbreviation or acronym from long-term memory.

  Parameters:
  abbr_acr: the clinical abbreviation or acronym to look up
  """
  try:
    key = _norm(abbr_acr)
    if not key:
      return None

    # LangGraph BaseStore API: get(namespace, key)
    if hasattr(store, "get") and callable(getattr(store, "get")):
      result = store.get(_ABBREVIATIONS_NAMESPACE, key)
      if result is None:
        return None
      value = result.value if hasattr(result, "value") else result
      if isinstance(value, dict):
        meaning = value.get("meaning")
        use_context = value.get("use_context")
        return f"Meaning: {meaning} \n Use context: {use_context}" if meaning else None
      return f"Stored value: {value}"

    # Fallback: dict-like store interface
    if hasattr(store, "mget"):
      composite_key = f"{_ABBREVIATIONS_NAMESPACE[0]}::{key}"
      results = store.mget([composite_key])
      if results and results[0]:
        value = results[0]
        if isinstance(value, dict):
          return f"Meaning: {value.get('meaning')} \n Use context: {value.get('use_context')}"
        return str(value)
      return None

    # Last resort: direct key access
    value = store.get(key)
    if isinstance(value, dict):
      return f"Meaning: {value.get('meaning')} \n Use context: {value.get('use_context')}"
    return str(value) if value else None

  except Exception as e:
    return f"Fail to retrieve abbreviations due to error: {e}"

# @tool
# def handoff_to_agent(normalized_note: str, agent_name: Literal["clinical_entity_extraction"], tool_call_id: Annotated[str, InjectedToolCallId]):
#   """
#   Hand off the normalized note to the specified agent.
#   Parameters:
#   normalized_note: the normalized note
#   agent_name: the name of the agent to hand off to (RxNorm or clinical_entity_extraction)
#   tool_call_id: the tool call id
#   """
#   update = {
#     "global_medical_state": {
#       "normalized_note": normalized_note,
#       "extracted_entities": [],
#       "resolved_relationship": []
#     },
#     "messages": [
#       ToolMessage(
#         name = f"handoff_to_{agent_name}_agent",
#         content = f"Successfully handed off to {agent_name} agent",
#         tool_call_id = tool_call_id
#       )
#     ]
#   }
#   return Command(
#     update = update,
#     goto = f"handoff_to_{agent_name}_agent"
#   )

@tool
async def normalize_text(normalized_text: NormalizedText, state: Annotated[BaseModel, InjectedState], tool_call_id: Annotated[str, InjectedToolCallId]) -> NormalizedText:
  """
  Normalize the text.
  Parameters:
  normalized_text: the normalized text
  """
  normalized_text = NormalizedText(normalized_text=normalized_text.normalized_text)
  update = {
    "messages": [ToolMessage(content=f"Normalized text: {normalized_text.normalized_text}", tool_call_id=tool_call_id)],
    "normalized_text": normalized_text
  }
  return Command(
    update=update
  )

# ------------- ENTITIES EXTRACTION TOOLS --------------

@tool
async def extract_entities(extracted_entities: ExtractedEntities, state: Annotated[BaseModel, InjectedState], tool_call_id: Annotated[str, InjectedToolCallId]) -> ExtractedEntities:
  """
  Extract the entities from the text.
  Parameters:
  extracted_entities: the extracted entities
  """
  extracted_entities = ExtractedEntities(extracted_entities=extracted_entities.extracted_entities)
  update = {
    "messages": [ToolMessage(content=f"Entities extracted", tool_call_id=tool_call_id)],
    "extracted_entities": extracted_entities
  }
  return Command(
    update=update
  )

# ------------- MAPPING TOOLS --------------
@tool
async def query_rxnconso(
    query: str = None,
    metadata_filter: Dict[str, Any] = None,
    k: int = 20
) -> List[str]:
    """
    Query RXNCONSO table via semantic search.

    Use for finding drug names. If query is None, uses filter_only mode.

    Parameters:
    query: Drug name to search (e.g., "Metformin")
    metadata_filter: Filters like {"TTY": "IN", "SUPPRESS": "N"}
    k: Number of results

    Returns:
    List of matching documents with RXCUI, TTY, STR
    """
    rxnconso_results = await _rag_service.milvus_sematic_search(
        collection_name="RXNCONSO",
        query=query,
        k=k,
        filter=_dict_to_milvus_filter(metadata_filter),
        output_fields=["rxcui", "tty", "str"]
    )
    return rxnconso_results


@tool
async def query_rxnrel(
    metadata_filter: Dict[str, Any],
) -> List[str]:
    """
    Query RXNREL table for relationships.

    Parameters:
    metadata_filter: REQUIRED - e.g., {"RXCUI1": "6809", "RELA": "isa"}

    Returns:
    List of relationship documents with RXCUI1, RXCUI2, RELA
    """
    conditions, values = _validate_filter(metadata_filter, "rxnorm_relationships")
    where_clause = " AND ".join(conditions)
    rxnrel_results = await _db_service.db_query(
        query=f"SELECT * FROM rxnorm_relationships WHERE {where_clause}",
        *values
    )
    return rxnrel_results


@tool
async def query_rxnsat(
    metadata_filter: Dict[str, Any],
) -> List[str]:
    """
    Query RXNSAT table for attributes (NDC, strength, etc.).

    Parameters:
    metadata_filter: REQUIRED - e.g., {"RXCUI": "316151", "ATN": "NDC"}

    Returns:
    List of attribute documents with ATN, ATV
    """
    conditions, values = _validate_filter(metadata_filter, "rxnorm_attributes")
    where_clause = " AND ".join(conditions)
    rxnsat_results = await _db_service.db_query(
        query=f"SELECT * FROM rxnorm_attributes WHERE {where_clause}",
        *values
    )
    return rxnsat_results


@tool
async def query_rxnsty(
    metadata_filter: Dict[str, Any],
) -> List[str]:
    """
    Query RXNSTY table for semantic type classification.

    Parameters:
    metadata_filter: REQUIRED - e.g., {"RXCUI": "316151", "TUI": "A1"}
    """
    conditions, values = _validate_filter(metadata_filter, "rxnorm_semantic_types")
    where_clause = " AND ".join(conditions)
    rxnsty_results = await _db_service.db_query(
        query=f"SELECT * FROM rxnorm_semantic_types WHERE {where_clause}",
        *values
    )
    return rxnsty_results


@tool
async def query_rxndoc(
    metadata_filter: Dict[str, Any],
) -> List[str]:
    """
    Query RXNDOC table for abbreviation / reference lookup.

    Parameters:
    metadata_filter: REQUIRED - e.g., {"KEY": "ATN"}

    Returns:
    List of documentation entries
    """
    conditions, values = _validate_filter(metadata_filter, "rxnorm_documentation")
    where_clause = " AND ".join(conditions)
    rxndoc_results = await _db_service.db_query(
        query=f"SELECT * FROM rxnorm_documentation WHERE {where_clause}",
        *values
    )
    return rxndoc_results


@tool
async def store_resolved_relationship(
    anchor_text: str,
    anchor_tty: str,
    is_combination: bool,
    resolution_path: str,
    components: List[Dict[str, Any]],
    final_concept: Dict[str, Any],
    confidence_score: float,
    state: Annotated[BaseModel, InjectedState],
):
    """
    Store completed ResolvedRelationship in global state.

    Parameters:
    anchor_text: Original drug name from note
    anchor_tty: Starting TTY (IN, BN, etc.)
    is_combination: True if multi-ingredient drug
    resolution_path: Traversal path (e.g., "IN -> SCDC -> SCD")
    components: List of ingredient components with hops
    final_concept: Dict with rxcui, tty, full_name, validation_metadata
    confidence_score: Float 0.0-1.0
    """
    components_string_list = []
    for component in components:
        component_string = f"ingredient_name: {component['ingredient_name']}, in_cui: {component['in_cui']}, strength: {component['strength']}, scdc_cui: {component['scdc_cui']}"
        components_string_list.append(component_string)
    final_concept_string = f"rxcui: {final_concept['rxcui']}, tty: {final_concept['tty']}, full_name: {final_concept['full_name']}"
    resolved_relationship = {
        "anchor_text": anchor_text,
        "anchor_tty": anchor_tty,
        "is_combination": is_combination,
        "resolution_path": resolution_path,
        "components": components_string_list,
        "final_concept": final_concept_string,
        "confidence_score": confidence_score
    }

    try:
        await _rag_service.runtime_milvus_ingest(
            collection_name="rxnorm_resolved_relationship",
            data=[resolved_relationship],
            vector_columns=["anchor_text"],
            scalar_columns=["anchor_text", "anchor_tty", "is_combination", "resolution_path", "components", "final_concept", "confidence_score"]
        )
        return f"Resolved relationship stored for customer {state.customer.id}"
    except Exception as e:
        return f"Error: {e}"


@tool
async def retrieve_resolved_relationship(
    anchor_text: str,
) -> List[Dict[str, Any]]:
    """
    Retrieve completed ResolvedRelationship from global state.

    Parameters:
    anchor_text: The anchor text to search for
    """
    try:
        resolved_relationship = await _rag_service.milvus_sematic_search(
            collection_name="rxnorm_resolved_relationship",
            query=anchor_text,
            k=10,
            filter="confidence_score >= 0.85",
            output_fields=["anchor_text", "anchor_tty", "is_combination", "resolution_path", "components", "final_concept", "confidence_score"]
        )
        return resolved_relationship
    except Exception as e:
        return f"Error: {e}"


@tool
async def store_mapping_results(
    results: list[dict],
    state: Annotated[BaseModel, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> str:
    """
    Store the final mapping results for all entities. Call this after ALL entities have been mapped.

    Parameters:
    results: List of mapping result dicts. Each must have:
        anchor_text, rxcui, str, tty, similarity_score, resolution_strategy, resolution_path, confidence_score

    Example:
    results = [
        {
            "anchor_text": "Metformin 500mg",
            "rxcui": "861007",
            "str": "Metformin 500 MG Oral Tablet",
            "tty": "SCD",
            "similarity_score": 0.97,
            "resolution_strategy": "direct",
            "resolution_path": "SCD direct",
            "confidence_score": 0.97
        }
    ]
    """
    mapping_results = []
    for r in results:
        mapping_results.append(MappingResult(
            anchor_text=r.get("anchor_text", ""),
            rxcui=r.get("rxcui", ""),
            str=r.get("str", ""),
            tty=r.get("tty", ""),
            similarity_score=r.get("similarity_score", 0.0),
            resolution_strategy=r.get("resolution_strategy", ""),
            resolution_path=r.get("resolution_path", ""),
            confidence_score=r.get("confidence_score", 0.0),
        ))
    return Command(update={
        "messages": [ToolMessage(
            content=f"Stored {len(mapping_results)} mapping results",
            tool_call_id=tool_call_id,
        )],
        "mapping_results": MappingResults(mapping_results=mapping_results),
    })

# ---------------------------------------------------------------

TOOLS = {
   "text_normalize_tools": [
        store_abbreviations,
        retrieve_abbreviations,
        normalize_text,
    ],
    "entity_extraction_tools": [
        extract_entities,
    ],
    "rxnorm_mapping_tools": [
      query_rxnconso,
      query_rxnrel,
      query_rxnsat,
      query_rxnsty,
      query_rxndoc,
      retrieve_resolved_relationship,
      store_resolved_relationship,
      store_mapping_results,
    ]
}


def get_tools() -> List[Callable]:
    return TOOLS
