"""
Tools for RxNorm Mapping Skill

Maps medication entities to RxNorm codes (SCD/SBD) with NDC codes.
"""
from langchain.tools import tool
from langchain.tools import InjectedStore
from typing import Annotated, List, Dict, Any, Callable
from langchain_core.tools import InjectedToolCallId
from langchain.tools import InjectedState, InjectedStore
from src.services.RAG_service import RAGService
from src.services.db_service import DBService
from src.services.agent_registry import get_agent_names
from langchain_huggingface import HuggingFaceEmbeddings
from pydantic import BaseModel
from src.infrastructure.milvus import get_milvus

_embedding_model = HuggingFaceEmbeddings(model_name="neuml/pubmedbert-base-embeddings")
_rag_service = RAGService(embedding_model=_embedding_model)
_db_service = DBService()
_agent_list = get_agent_names()

def _dict_to_milvus_filter(metadata_filter: Dict[str, Any] | None) -> str | None:
    """Convert a dict of field=value pairs to a Milvus filter expression string.

    Milvus search() requires filter as a SQL-like string, not a dict.
    Example: {"TTY": "IN", "SUPPRESS": "N"} → "TTY == 'IN' and SUPPRESS == 'N'"
    """
    if not metadata_filter:
        return None
    clauses = [
        f"{key.lower()} == '{value}'" if isinstance(value, str) else f"{key.lower()} == {value}"
        for key, value in metadata_filter.items()
    ]
    return " and ".join(clauses)


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
    where_clause = " AND ".join([f"{key} = '{value}'" for key, value in metadata_filter.items()])
    rxnrel_results = await _db_service.db_query(
        query=f"SELECT * FROM rxnorm_relationships WHERE {where_clause}"
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
    where_clause = " AND ".join([f"{key} = '{value}'" for key, value in metadata_filter.items()])
    rxnsat_results = await _db_service.db_query(
        query=f"SELECT * FROM rxnorm_attributes WHERE {where_clause}"
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
    where_clause = " AND ".join([f"{key} = '{value}'" for key, value in metadata_filter.items()])
    rxnsty_results = await _db_service.db_query(
        query=f"SELECT * FROM rxnorm_semantic_types WHERE {where_clause}"
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
    where_clause = " AND ".join([f"{key} = '{value}'" for key, value in metadata_filter.items()])
    rxndoc_results = await _db_service.db_query(
        query=f"SELECT * FROM rxnorm_documentation WHERE {where_clause}"
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

TOOLS = [
    query_rxnconso,
    query_rxnrel,
    query_rxnsty,
    query_rxndoc,
    retrieve_resolved_relationship,
    store_resolved_relationship,
]
def get_tools() -> List[Callable]:
    return TOOLS