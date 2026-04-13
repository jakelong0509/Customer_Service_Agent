from src.services.agent_registry import get_agent
from src.core.agent_run_request_model import AgentRunRequest
from src.infrastructure.milvus import init_milvus
from src.infrastructure.database import init_pool
from DAL.customerDA import CustomerDA
from src.services.agent_registry import create_agent
import src.agents.shared_tools
from dotenv import load_dotenv
load_dotenv()
import os
import asyncio
import selectors

if "LANGSMITH_API_KEY" not in os.environ:
    os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
    os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGSMITH_PROJECT")
    os.environ["LANGSMITH_TRACING"] = os.getenv("LANGSMITH_TRACING")
    os.environ["LANGSMITH_ENDPOINT"] = os.getenv("LANGSMITH_ENDPOINT")
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Messy note: informal structure, abbreviations, run-ons — exercises normalize → extract → RxNorm map.
# Expected RxNorm SCD-style RXCUIs when mapping succeeds (verify against your RxNorm month):
# - Metformin 500 mg oral tablet: 861007
# - Lisinopril 10 mg oral tablet: 314076
# - Atorvastatin 20 mg oral tablet: 617310
# - Aspirin 81 mg oral tablet: 318272
# - Omeprazole 20 mg delayed release oral capsule: 198051
# - Rosuvastatin 10 mg oral tablet: 859747 (secondary statin if extraction picks it up)
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


async def main():
  init_milvus()
  await init_pool()
  create_agent()
  agent = get_agent("rxnorm_mapping_agent_email")
  assert agent is not None

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

if __name__ == "__main__":
  asyncio.run(main(), loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
