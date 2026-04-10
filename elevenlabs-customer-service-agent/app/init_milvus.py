import sys
from pathlib import Path
from src.infrastructure.milvus import init_milvus
from langchain_huggingface import HuggingFaceEmbeddings
from src.infrastructure.database import init_pool
import torch
import asyncio

RXNCONSO_COLUMNS = ["RXCUI", "LAT", "TS", "LUI", "STT", "SUI", "ISPREF", "RXAUI", "SAUI", "SCUI", "SDUI", "SAB", "TTY", "CODE", "STR", "SRL", "SUPPRESS", "CVF"]
RXNDOC_COLUMNS = ["KEY", "VALUE", "TYPE", "EXPL"]
RXNSAT_COLUMNS = ["RXCUI", "LUI", "SUI", "RXAUI", "STYPE", "CODE", "ATUI", "SATUI", "ATN", "SAB", "ATV", "SUPPRESS", "CVF"]
RXNSTY_COLUMNS = ["RXCUI", "TUI", "STN", "STY", "ATUI", "CVF"]
RXNREL_COLUMNS = ["RXCUI1", "RXAUI1", "STYPE1", "REL", "RXCUI2", "RXAUI2", "STYPE2", "RELA", "RUI", "SRUI", "SAB", "SL", "RG", "DIR", "SUPPRESS", "CVF"]

async def milvus_ingest():
    # Initialize Milvus client first
    init_milvus()
    from src.services.RAG_service import RAGService
    embedding_model = HuggingFaceEmbeddings(model_name="neuml/pubmedbert-base-embeddings")
    rag_service = RAGService(embedding_model=embedding_model)
    
    await rag_service.ingest_local(
        file_path="D:/Medical_terms_codes/RxNORM/RXNCONSO.RRF",
        collection_name="RXNCONSO",
        vector_columns=["STR"],
        scalar_columns=["RXCUI", "LAT", "TS", "LUI", "STT", "SUI", "ISPREF", "RXAUI", "SAUI", "SCUI", "SDUI", "SAB", "TTY", "CODE", "STR", "SRL", "SUPPRESS", "CVF"],
        batch_size=128,
        insert_filter_equals={"SAB": "RXNORM", "LAT": "ENG"},
        insert_filter_not_equals={"SUPPRESS": "Y"}
    )

async def db_ingest():
    await init_pool()
    from src.services.db_service import DBService
    db_service = DBService()
    table_names_dict = {
        "RXNSAT": "rxnorm_attributes",
        "RXNSTY": "rxnorm_semantic_types",
        "RXNDOC": "rxnorm_documentation",
        "RXNREL": "rxnorm_relationships",
    }
    table_columns_dict = {
        "RXNSAT": [col.lower() for col in RXNSAT_COLUMNS],
        "RXNSTY": [col.lower() for col in RXNSTY_COLUMNS],
        "RXNDOC": [col.lower() for col in RXNDOC_COLUMNS],
        "RXNREL": [col.lower() for col in RXNREL_COLUMNS],
    }
    for rxname, dbname in table_names_dict.items():
        await db_service.ingest_local(
            file_path=f"D:/Medical_terms_codes/RxNORM/{rxname}.RRF",
            table_name=dbname,
            columns=table_columns_dict[rxname]
        )

if __name__ == "__main__":
    asyncio.run(db_ingest())