from abc import ABC, abstractmethod
from langgraph.graph import StateGraph, START, END
from src.core.agent_run_request_model import AgentRunRequest
from src.core.conversation import CallContext
from src.core.customer import CustomerModel

class AgentBase(ABC):
  @abstractmethod
  def run(self, request: AgentRunRequest, context: CallContext, customer: CustomerModel) -> str:
    raise NotImplementedError("Subclasses must implement this method")

  def build_graph(self) -> StateGraph:
    raise NotImplementedError("Subclasses must implement this method")