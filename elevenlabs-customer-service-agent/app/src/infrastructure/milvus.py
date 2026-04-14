import sys
from pymilvus import MilvusClient
from src.core.config import get_settings

# singleton pattern
_client: MilvusClient | None = None


def _canonical_module():
    """Return the canonical module object (src.infrastructure.milvus).

    Prevents double-import divergence when both ``src.infrastructure.milvus``
    and ``app.src.infrastructure.milvus`` are loaded due to overlapping
    PYTHONPATH entries.
    """
    return sys.modules.get("src.infrastructure.milvus", sys.modules.get("app.src.infrastructure.milvus"))


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
        print(f"Milvus client initialized: {_client}")
        # Ensure the canonical module also sees the client
        mod = _canonical_module()
        if mod is not None and mod is not sys.modules[__name__]:
            mod.__dict__["_client"] = _client
        return _client
    except Exception as e:
        print(f"ERROR: Failed to initialize Milvus: {e}")
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"Milvus initialization failed: {e}") from e


def get_milvus() -> MilvusClient:
    global _client
    # Check canonical module's client if ours is None
    if _client is None:
        mod = _canonical_module()
        if mod is not None and mod is not sys.modules[__name__]:
            _client = mod.__dict__.get("_client")
    if _client is None:
        raise RuntimeError("Milvus client is not initialized. Call init_milvus() at startup.")
    return _client


def close_milvus() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
    # Also clear the canonical module
    mod = _canonical_module()
    if mod is not None and mod is not sys.modules[__name__]:
        mod.__dict__["_client"] = None
