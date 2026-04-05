from pymilvus import MilvusClient, DataType
from dotenv import load_dotenv
import os

load_dotenv()

# singleton pattern
_client: MilvusClient | None = None
async def init_milvus() -> MilvusClient:
  global _client
  _client = MilvusClient(
    uri=os.getenv("MILVUS_CLUSTER_ENDPOINT"),
    api_key=os.getenv("MILVUS_API_KEY"),
  )
  return _client

def get_milvus() -> MilvusClient:
  if _client is None:
    return RuntimeError("Milvus client is not initialized. Call init_milvus() at startup.")
  return _client

async def close_milvus() -> None:
  global _client
  if _client is not None:
    await _client.close()
    _client = None

