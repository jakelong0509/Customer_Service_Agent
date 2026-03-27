from abc import ABC, abstractmethod
from langgraph.graph import StateGraph, START, END
from src.core.agent_run_request_model import AgentRunRequest
from src.core.conversation import CallContext
from src.core.customer import CustomerModel
from langchain_core.tools import tool

class AgentBase(ABC):
  @abstractmethod
  def run(self, request: AgentRunRequest, customer: CustomerModel) -> str:
    raise NotImplementedError("Subclasses must implement this method")

  def build_graph(self) -> StateGraph:
    raise NotImplementedError("Subclasses must implement this method")

  @tool
  async def activate_skill(self, skill_name: str) -> None:
    """Activate a skill
    Args:
      skill_name: str - The name of the skill to activate
    """
    raise NotImplementedError("Subclasses must implement this method")
  
  @tool
  async def deactivate_skill(self, skill_name: str) -> None:
    """Deactivate a skill
    Args:
      skill_name: str - The name of the skill to deactivate
    """
    raise NotImplementedError("Subclasses must implement this method")
  