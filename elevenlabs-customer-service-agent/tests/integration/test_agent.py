import asyncio
import os
import pytest

from app.src.services.agent_registry import create_agent, AGENTS, get_agent
from app.src.infrastructure.milvus import init_milvus, close_milvus
from app.src.infrastructure.database import init_pool, close_pool



# def test_initialize_milvus():
#     """Initialize Milvus and DB with timeout, cleanup after test."""
#     print("Checking if services are configured")
#     # Run sync init_milvus in thread with timeout
#     try:
#         init_milvus()
#         print("Milvus initialized")
#     except asyncio.TimeoutError:
#         pytest.skip("Milvus connection timeout - server not reachable")

# @pytest.mark.asyncio(loop_scope="module") 
# async def test_initialize_database():
#     """Initialize database with timeout, cleanup after test."""
#     print("Checking if database is configured")
#     try:
#         await asyncio.wait_for(init_pool(), timeout=10.0)
#         print("Database initialized")
#     except asyncio.TimeoutError:
#         pytest.skip("Database connection timeout")

# def test_create_agent():
#     """Test that agents are created properly."""
#     create_agent()
#     assert len(AGENTS) > 0
#     assert "customer_support_agent" in AGENTS
#     assert "security_agent" in AGENTS


@pytest.mark.asyncio(loop_scope="module")
async def test_rxnorm_mapping_agent():
    """Test RxNorm mapping agent functionality."""
    init_milvus()
    await asyncio.wait_for(init_pool(), timeout=10.0)
    create_agent()
    agent = get_agent("rxnorm_mapping_agent_email")
    assert agent is not None
    
    response = await agent.arun("I need to map the following medication to RxNorm: Metformin 500mg")
    assert response is not None
    assert "Metformin 500mg" in response
    assert "861007" in response
    assert "0093-1074-01" in response
