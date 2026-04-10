from src.services.agent_registry import get_agent
from src.core.agent_run_request_model import AgentRunRequest
from src.core.conversation import CallContext
from src.core.customer import CustomerModel
from src.infrastructure.milvus import init_milvus
from src.infrastructure.database import init_pool
from DAL.customerDA import CustomerDA
from src.services.agent_registry import create_agent
import src.agents.shared_tools
from dotenv import load_dotenv
load_dotenv()
import os
import asyncio
if "LANGSMITH_API_KEY" not in os.environ:
    os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
    os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGSMITH_PROJECT")
    os.environ["LANGSMITH_TRACING"] = os.getenv("LANGSMITH_TRACING")
    os.environ["LANGSMITH_ENDPOINT"] = os.getenv("LANGSMITH_ENDPOINT")
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

async def main():
  init_milvus()
  await init_pool()
  create_agent()
  agent = get_agent("rxnorm_mapping_agent_email")
  assert agent is not None
  clinical_note = """
SUBJECTIVE:
Chief complaint: Follow-up for type 2 diabetes mellitus and hypertension.

History of present illness:
58-year-old male with established T2DM (HbA1c 7.8% three months ago) and HTN presents
for routine clinic follow-up. He reports good adherence to medications. Denies hypoglycemia,
polyuria, polydipsia, or chest pain. Walks 20 minutes daily. Diet unchanged.

Past medical history: T2DM, essential hypertension, dyslipidemia.

Medications (home):
- Metformin 500mg PO BID with meals
- Lisinopril 10mg PO daily
- Atorvastatin 20mg PO QHS

Allergies: NKDA.

OBJECTIVE:
Vitals: BP 128/80, HR 72, RR 16, T 98.2°F, BMI 29.
General: Alert, no acute distress.
CV: Regular rate and rhythm, no murmur.
Feet: Monofilament intact bilaterally.

ASSESSMENT:
1. Type 2 diabetes mellitus — suboptimally controlled, improving adherence.
2. Essential hypertension — at goal on current regimen.

PLAN:
- Continue Metformin 500mg BID; recheck HbA1c in 3 months.
- Continue lisinopril and atorvastatin.
- Reinforce diet and exercise counseling; diabetic foot care reviewed.

Electronically signed: Dr. Demo, MD | Date: 2026-04-09
""".strip()

  request = AgentRunRequest(
    agent_name="rxnorm_mapping_agent_email",
    request=clinical_note,
  )
  customer = await CustomerDA().get_customer_by_email_address("jakelong0509@gmail.com")
  response = await agent.arun(request, customer, "test-session-id")
  assert response is not None
  assert "Metformin 500mg" in response
  assert "861007" in response
  assert "0093-1074-01" in response

if __name__ == "__main__":
  asyncio.run(main())
