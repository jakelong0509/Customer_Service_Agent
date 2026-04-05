# RAG service will be responsible for handling retrieval-augmented generation tasks
# 1. ingest data into Milvus vector database
# 2. query Milvus for relevant data based on user input
# 3. return retrieved data to agent for use in response generation
# 4. Insert data into Relational DB (PostgreSQL)
# 5. Query data from Relational DB (PostgreSQL)

from fileinput import filename
from typing import List, Dict
from src.infrastructure.milvus import get_milvus
from src.infrastructure.database import get_db_pool
from src.utils.RRFLoader import RRFLoader
from langchain_core.embeddings import Embeddings
import sys
from pathlib import Path
from pymilvus import DataType

# Ensure project root is on path so RRF can be imported
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
  sys.path.insert(0, str(_project_root))

import warnings
warnings.filterwarnings('ignore')

RXNCONSO_COLUMNS = ["RXCUI", "LAT", "TS", "LUI", "STT", "SUI", "ISPREF", "RXAUI", "SAUI", "SCUI", "SDUI", "SAB", "TTY", "CODE", "STR", "SRL", "SUPPRESS", "CVF"]
RXNDOC_COLUMNS = ["KEY", "VALUE", "TYPE", "EXPL"]
RXNSAT_COLUMNS = ["RXCUI", "LUI", "SUI", "RXAUI", "STYPE", "CODE", "ATUI", "SATUI", "ATN", "SAB", "ATV", "SUPPRESS", "CVF"]
RXNSTY_COLUMNS = ["RXCUI", "TUI", "STN", "STY", "ATUI", "CVF"]
RXNREL_COLUMNS = ["RXCUI1", "RXAUI1", "STYPE1", "REL", "RXCUI2", "RXAUI2", "STYPE2", "RELA", "RUI", "SRUI", "SAB", "SL", "RG", "DIR", "SUPPRESS", "CVF"]

_RRF_COLUMNS_BY_FILENAME = {
  "RXNCONSO": RXNCONSO_COLUMNS,
  "RXNDOC": RXNDOC_COLUMNS,
  "RXNSAT": RXNSAT_COLUMNS,
  "RXNSTY": RXNSTY_COLUMNS,
  "RXNREL": RXNREL_COLUMNS,
}

_milvus_client = get_milvus()
_db_pool = get_db_pool()

class RAGService:
  def __init__(
      self,
      embedding_model: Embeddings
  ):
    self._embedding_model = embedding_model

  async def _embed_text(self, texts: List[str]) -> List[List[float]]:
    vector = await self._embedding_model.embed_documents(texts)
    return vector
  
  async def ingest_local(
      self, 
      file_path: str, 
      collection_name: str, 
      vector_columns: List[str],
      scalar_columns: List[str] = None,
      batch_size: int = 128,
      insert_filter_equals: Dict[str, str] = None,
      insert_filter_not_equals: Dict[str, str] = None
  ) -> None:
    """Ingest file into Milvus vector database
    Args:
        file_path: path to file to ingest
        collection_name: name of Milvus collection to ingest into
        vector_columns: list of column names to use for vectorization (will be concatenated if multiple)
        scalar_columns: list of column names to include as metadata (non-vector) in Milvus
        batch_size: number of rows to process in each batch for embedding and insertion
        insert_filter_equals: optional dict of column-value pairs to filter rows for insertion (only insert rows where column equals value)
        insert_filter_not_equals: optional dict of column-value pairs to filter rows for insertion (only insert rows where column does not equal value)
    """
    assert collection_name != "", "Collection name must be provided"
    assert len(vector_columns) > 0, "At least one vector column must be provided"
    
    loader = None
    # get file extension and verify it's .RRF
    if Path(file_path).suffix == ".RRF":
      # We will only read the columns needed for vectorization and metadata (if pk_column is provided)
      loader = RRFLoader(filePath=file_path, columns=[*scalar_columns, *vector_columns] if scalar_columns else vector_columns, batchSize=batch_size)
    else:
      print(f"Unsupported file type for file {file_path}. Only .RRF files are supported.")
      return
     
    document_stream = loader.lazy_load()
    for chunk in document_stream:
      rows_to_embed = []
      for row in chunk:
          if insert_filter_equals:
            if any(row.get(col) != val for col, val in insert_filter_equals.items()):
                continue  # skip rows that don't match the equals filter
          if insert_filter_not_equals:
            if any(row.get(col) == val for col, val in insert_filter_not_equals.items()):
                continue  # skip rows that match the not equals filter
            
          # if multiple vector columns, concatenate them for embedding
          str_concatenated = " ".join([row[col] for col in vector_columns if col in row])

          if not str_concatenated.strip():  # skip rows with empty text
              continue   # skip rows with no text
          row_dict = {}
          for col in scalar_columns:
            row_dict[col.lower()] = row[col] if col in row else None
          row_dict["str"] = str_concatenated
          row_dict["vector"] = None  # placeholder for vector
          rows_to_embed.append(row_dict)
          
      # Embed
      texts = [d["str"] for d in rows_to_embed]
      if not texts:
          continue

      embeddings = await self._embed_text(texts)
      for i, emb in enumerate(embeddings):
          rows_to_embed[i]["vector"] = emb

      # Insert into Zilliz — every row
      _milvus_client.insert(
          collection_name=collection_name,
          data=rows_to_embed,
      )

      print(f"Ingested batch: {len(rows_to_embed)} entities")
