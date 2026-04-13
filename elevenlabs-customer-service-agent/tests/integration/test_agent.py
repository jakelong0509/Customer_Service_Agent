import asyncio
import os
import pytest

from app.src.services.agent_registry import create_agent, AGENTS, get_agent
from app.src.infrastructure.milvus import init_milvus, close_milvus
from app.src.infrastructure.database import init_pool, close_pool
from app.src.core.agent_run_request_model import AgentRunRequest
from app.DAL.customerDA import CustomerDA


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
    
    _MESSY_CLINICAL_NOTE = """
        SUBJECTIVE / CC:
        f/u for dm2 + htn + gerd + "numb toes" — 58 y/o male, established pt

        HPI (rambling):
        comes in for routine stuff, says he's "mostly" taking his pills ok lol
        last A1c like 7.8% few months back. denies CP/SOB. walks sometimes.
        reflux acting up if he eats late — takes something for it. tingling in feet off/on.

        home meds (per patient — list is messy / duplicates / random order):
        - metformin 500mg po bid w meals (sometimes skips dinner dose)
        - ACE-I: lisinopril 10 mg po qd
        - for cholesterol: atorva 20mg po qhs @ bedtime AND also rosuva 10mg qd (yes both — long story, don't ask)
        - baby asa 81mg qam "for heart" (pt not sure if prescribed or OTC)
        - prilosec / omeprazole 20mg qd before bfast for heartburn
        - neurontin? gabapentin 300mg tid for feet (thinks it helps)
        - tylenol prn headaches (650mg sometimes)

        ALLERGIES: nkda

        ASSESSMENT:
        1. T2DM w/ neuropathy sx
        2. HTN
        3. dyslipidemia (on dual lipid therapy per pt report — verify)
        4. GERD
        5. HA prn

        PLAN:
        continue current regimen where appropriate; reconcile statins; recheck labs; blah blah counseling

        Electronically signed: Dr Demo | 4/9/2026
    """.strip()

    request = AgentRunRequest(
        agent_name="rxnorm_mapping_agent_email",
        request=_MESSY_CLINICAL_NOTE,
    )
    customer = await CustomerDA().get_customer_by_email_address("jakelong0509@gmail.com")
    response = await agent.arun(request, customer, "test-session-id-3")
    assert response is not None

    # Manual inspection: normalization + entity extraction + mapping quality
    print("\n---------- Agent response (messy note test) ----------\n")
    print(response)
    print("\n---------- End response ----------\n")

    # Core drugs from the messy note should map to stable RxNorm concepts when the pipeline succeeds
    assert "861007" in response, "Expected Metformin 500mg (oral tablet) RXCUI in mapped output"
    assert "314076" in response, "Expected Lisinopril 10mg RXCUI in mapped output"
    assert "617310" in response, "Expected Atorvastatin 20mg RXCUI in mapped output"
    assert "318272" in response, "Expected Aspirin 81mg RXCUI in mapped output"
    assert "198051" in response, "Expected Omeprazole 20mg DR capsule RXCUI in mapped output"
