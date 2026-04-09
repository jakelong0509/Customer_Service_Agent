from pymilvus import MilvusClient
from src.core.config import get_settings

# singleton pattern
_client: MilvusClient | None = None

def init_milvus(timeout: float = 30.0) -> MilvusClient | None:
    """Initialize Milvus/Zilliz Cloud client.

    For Zilliz Cloud serverless, set MILVUS_CLUSTER_ENDPOINT to the public HTTPS URL
    **including port 443**, e.g. ``https://in03-xxx.cloud.zilliz.com:443`` — if you omit
    the port, PyMilvus defaults to 19530 and the connection will fail.

    - MILVUS_COLLECTION_TOKEN: API key or ``user:password`` from the console
    
    Args:
        timeout: Connection timeout in seconds (default 30s for cloud)
        
    Returns:
        MilvusClient if successful, None if not configured
    """
    global _client
    settings = get_settings()
    # Skip if not configured
    if not settings.milvus_cluster_endpoint:
        return None
    
    try:
        _client = MilvusClient(
            uri=settings.milvus_cluster_endpoint,
            token=settings.milvus_collection_token or "",
            timeout=timeout,
        )
        return _client
    except Exception as e:
        print(f"Failed to initialize Milvus: {e}")
        return None

def get_milvus() -> MilvusClient:
  if _client is None:
    raise RuntimeError("Milvus client is not initialized. Call init_milvus() at startup.")
  return _client

def close_milvus() -> None:
  global _client
  if _client is not None:
    _client.close()
    _client = None

