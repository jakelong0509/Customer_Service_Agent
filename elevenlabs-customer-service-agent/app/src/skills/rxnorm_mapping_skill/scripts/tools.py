"""
Tools for RxNorm Mapping Skill

Maps medication entities to RxNorm codes (SCD/SBD) with NDC codes.
"""
from langchain.tools import tool
from typing import Annotated, List, Dict, Any, Callable
from langchain_core.tools import InjectedToolCallId
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from src.services.RAG_service import RAGService
from src.services.db_service import DBService
from langchain_huggingface import HuggingFaceEmbeddings

_embedding_model = HuggingFaceEmbeddings(model_name="neuml/pubmedbert-base-embeddings")
_rag_service = RAGService(embedding_model=_embedding_model)
_db_service = DBService()

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
        filter=metadata_filter,
        output_fields=["RXCUI", "TTY", "STR"]
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
def store_resolved_relationship(
    anchor_text: str,
    anchor_tty: str,
    is_combination: bool,
    resolution_path: str,
    components: List[Dict[str, Any]],
    final_concept: Dict[str, Any],
    confidence_score: float,
    tool_call_id: Annotated[str, InjectedToolCallId],
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
    tool_call_id: Injected tool call ID
    """
    resolved_relationship = {
        "anchor_text": anchor_text,
        "anchor_tty": anchor_tty,
        "is_combination": is_combination,
        "resolution_path": resolution_path,
        "components": components,
        "final_concept": final_concept,
        "confidence_score": confidence_score
    }
    
    return Command(
        update={
            "global_medical_state": {
                "resolved_relationship": [resolved_relationship]
            },
            "messages": [
                ToolMessage(
                    name="store_resolved_relationship",
                    content=f"Stored resolution for: {anchor_text} -> RXCUI: {final_concept.get('rxcui', 'unknown')}",
                    tool_call_id=tool_call_id
                )
            ]
        },
        goto="end"  # End of workflow
    )

TOOLS = [query_rxnconso, query_rxnrel, query_rxnsat, query_rxnsty, query_rxndoc, store_resolved_relationship]
def get_tools() -> List[Callable]:
    return TOOLS