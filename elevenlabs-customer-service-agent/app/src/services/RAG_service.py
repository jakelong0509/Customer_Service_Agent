# RAG service will be responsible for handling retrieval-augmented generation tasks
# 1. ingest data into Milvus vector database
# 2. query Milvus for relevant data based on user input
# 3. return retrieved data to agent for use in response generation

from fileinput import filename
from typing import List, Dict
from src.infrastructure.milvus import get_milvus
from src.utils.RRFLoader import RRFLoader
from langchain_core.embeddings import Embeddings
import sys
from pathlib import Path
from pymilvus import DataType, RRFRanker, AnnSearchRequest

# Ensure project root is on path so RRF can be imported
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
  sys.path.insert(0, str(_project_root))

import warnings
warnings.filterwarnings('ignore')

class RAGService:
  def __init__(
      self,
      embedding_model: Embeddings
  ):
    self._embedding_model = embedding_model

  @staticmethod
  def _get_client():
    """Lazy Milvus client accessor, avoids module level import crash."""
    return get_milvus()

  async def _embed_text(self, texts: List[str]) -> List[List[float]]:
    vector = await self._embedding_model.aembed_documents(texts)
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
      loader = RRFLoader(filePath=file_path, columns=scalar_columns, batchSize=batch_size)
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
      self._get_client().insert(
          collection_name=collection_name,
          data=rows_to_embed,
      )

  async def runtime_milvus_ingest(
    self,
    collection_name: str,
    data: List[Dict],
    vector_columns: List[str],
    scalar_columns: List[str],
  ) -> None:
    """Ingest data into Milvus vector database at runtime
    Args:
        collection_name: name of Milvus collection to ingest into
        data: list of dictionaries to ingest
        vector_columns: list of column names to use for vectorization (will be concatenated if multiple)
        scalar_columns: list of column names to include as metadata (non-vector) in Milvus
    """
    assert collection_name != "", "Collection name must be provided"
    assert data != "", "Data must be provided"
    assert vector_columns != "", "Vector columns must be provided"
    assert scalar_columns != "", "Scalar columns must be provided"
    rows_to_embed = []
    for row in data:
      str_concatenated = " ".join([row[col] for col in vector_columns if col in row])
      if not str_concatenated.strip():
        continue
      row_dict = {}
      for col in scalar_columns:
        row_dict[col.lower()] = row[col] if col in row else None
      row_dict["vector"] = (await self._embed_text([str_concatenated]))[0]
      rows_to_embed.append(row_dict)

    self._get_client().insert(
      collection_name=collection_name,
      data=rows_to_embed
    )


  async def milvus_hybrid_search(
      self,
      collection_name: str,
      query: str,
      k: int = 10,
      filter: str = None,
      output_fields: List[str] = None
  ) -> List[Dict]:
    """Perform hybrid search in Milvus
    Args:
        collection_name: name of Milvus collection to search in
        query: search query string
        k: number of results to return
        filter: optional filter string in SQL-like syntax
    """
    assert collection_name != "", "Collection name must be provided"
    assert query != "", "Query must be provided"
    assert k > 0, "k must be greater than 0"

    # Embed query
    query_embedding = await self._embed_text([query])
    query_embedding = query_embedding[0]

    request = AnnSearchRequest(
      data=[query_embedding],
      anns_field="vector",
      limit=k,
      param = {
        "metric_type": "COSINE",
        "params": {
          "level": 3
        }
      },
      expr = filter
    )

    results = self._get_client().hybrid_search(
      collection_name=collection_name,
      reqs = [request],
      ranker = RRFRanker(),
      output_fields=output_fields,
      limit=k
    )
    return results

  def milvus_scalar_search(
      self,
      collection_name: str,
      filter: str = None,
      output_fields: List[str] = None
  ) -> List[Dict]:
    """Perform scalar search in Milvus
    Args:
        collection_name: name of Milvus collection to search in
        filter: optional filter string in SQL-like syntax
        output_fields: optional list of field names to return
    """
    assert collection_name != "", "Collection name must be provided"
    assert filter != "", "Filter must be provided"

    # Search
    results = self._get_client().query(
      collection_name=collection_name,
      filter=filter,
      output_fields=output_fields
    )
    return results

  async def milvus_sematic_search(
      self,
      collection_name: str,
      query: str,
      k: int = 10,
      filter: str = None,
      output_fields: List[str] = None
  ) -> List[Dict]:
    """Perform semantic search in Milvus
    Args:
        collection_name: name of Milvus collection to search in
        query: search query string
        k: number of results to return
        filter: optional filter string in SQL-like syntax
        output_fields: optional list of field names to return
    """
    assert collection_name != "", "Collection name must be provided"
    assert query != "", "Query must be provided"
    assert k > 0, "k must be greater than 0"

    # Embed query
    query_embedding = await self._embed_text([query])
    query_embedding = query_embedding[0]

    # Search
    results = self._get_client().search(
      collection_name=collection_name,
      data=[query_embedding],
      limit=k,
      filter=filter,
      output_fields=output_fields
    )
     # Flatten: results[0] is the list of hits for our single query
    if results and len(results) > 0:
        return results[0]  # ← Return just the hits, not wrapped in outer list
    return []

