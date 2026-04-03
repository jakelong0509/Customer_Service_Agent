from app.src.services.agent_registry import create_agent, AGENTS
from app.src.agents.shared_tools.skill_tools import activate_skill, deactivate_skill
from app.src.agents.shared_tools.memory_tools import retrieve_conversation_history, store_conversation_history, store_session_outcome, find_similar_sessions

def test_create_agent():
  create_agent()
  assert len(AGENTS) > 0
  assert "customer_support_agent" in AGENTS
  assert "security_agent" in AGENTS
  print("Agent Create test passed")

