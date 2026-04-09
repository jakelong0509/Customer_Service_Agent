from abc import ABC, abstractmethod
from langgraph.graph import StateGraph, START, END
from src.core.agent_run_request_model import AgentRunRequest
from src.core.customer import CustomerModel

class AgentBase(ABC):
  @abstractmethod
  async def arun(self, request: AgentRunRequest, customer: CustomerModel, session_id: str) -> str:
    raise NotImplementedError("Subclasses must implement this method")

  @abstractmethod
  def build_graph(self) -> StateGraph:
    raise NotImplementedError("Subclasses must implement this method")
