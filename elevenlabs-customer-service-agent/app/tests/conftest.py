import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "integration: integration tests requiring DB/Redis/Milvus")
    config.addinivalue_line("markers", "evaluation: LLM output quality evaluation tests")

@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    import asyncio
    for item in items:
        if asyncio.iscoroutinefunction(item.obj):
            item.add_marker(pytest.mark.asyncio)
