from src.agents.customer_support_agent.agent import agent_voice
from src.core.agent_run_request_model import AgentRunRequest
from src.core.conversation import CallContext
from src.core.customer import CustomerModel
from dotenv import load_dotenv
load_dotenv()
import os
if "LANGSMITH_API_KEY" not in os.environ:
    os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
    os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGSMITH_PROJECT")
    os.environ["LANGSMITH_TRACING"] = os.getenv("LANGSMITH_TRACING")
    os.environ["LANGSMITH_ENDPOINT"] = os.getenv("LANGSMITH_ENDPOINT")
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

if __name__ == "__main__":
  _req_base = AgentRunRequest(
    agent_name="customer_support_agent",
    request=(
      "TASK: appointments | Peer asks what is required before create_appointment may be called. "
      "Reply with STATUS and MISSING_FIELDS only."
    ),
  )
  _ctx_empty = CallContext(call_sid="test-call-no-customer", from_number="")
  _customer_empty = CustomerModel(
    id="",
    phone="",
    email="",
    name="",
    plan="",
    status="",
  )
  print("--- run 1: no customer information (empty CustomerModel) ---")
  print(agent_voice.run(_req_base, _ctx_empty, _customer_empty))

  _req_with_customer = AgentRunRequest(
    agent_name="customer_support_agent",
    request=(
      "TASK: appointments | customer_id=cust-422 | scheduled_at=2099-01-15T15:00:00Z | "
      "subject=billing review | status=scheduled | notes=from peer agent test"
    ),
  )
  _ctx_filled = CallContext(call_sid="test-call-with-customer", from_number="+15551234567")
  _customer_filled = CustomerModel(
    id="cust-422",
    phone="+15551234567",
    email="jane@example.com",
    name="Jane Doe",
    plan="pro",
    status="active",
  )
  print("--- run 2: with customer information ---")
  print(agent_voice.run(_req_with_customer, _ctx_filled, _customer_filled))