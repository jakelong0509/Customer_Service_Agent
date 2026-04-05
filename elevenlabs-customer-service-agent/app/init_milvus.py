import sys
from pathlib import Path
from src.infrastructure.milvus import init_milvus
from langchain_huggingface import HuggingFaceEmbeddings
import torch
import asyncio

RXNCONSO_COLUMNS = ["RXCUI", "LAT", "TS", "LUI", "STT", "SUI", "ISPREF", "RXAUI", "SAUI", "SCUI", "SDUI", "SAB", "TTY", "CODE", "STR", "SRL", "SUPPRESS", "CVF"]
RXNDOC_COLUMNS = ["KEY", "VALUE", "TYPE", "EXPL"]
RXNSAT_COLUMNS = ["RXCUI", "LUI", "SUI", "RXAUI", "STYPE", "CODE", "ATUI", "SATUI", "ATN", "SAB", "ATV", "SUPPRESS", "CVF"]
RXNSTY_COLUMNS = ["RXCUI", "TUI", "STN", "STY", "ATUI", "CVF"]
RXNREL_COLUMNS = ["RXCUI1", "RXAUI1", "STYPE1", "REL", "RXCUI2", "RXAUI2", "STYPE2", "RELA", "RUI", "SRUI", "SAB", "SL", "RG", "DIR", "SUPPRESS", "CVF"]

async def main():
    # Initialize Milvus client first
    await init_milvus()
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

if __name__ == "__main__":
    asyncio.run(main())