from abc import ABC, abstractmethod
from langgraph.graph import StateGraph, START, END
from app.api.routes import AgentRunRequest
from app.models.conversation import CallContext

class AgentBase(ABC):
  @abstractmethod
  def run(self, request: AgentRunRequest, context: CallContext) -> str:
    raise NotImplementedError("Subclasses must implement this method")

  def build_graph(self) -> StateGraph:
    raise NotImplementedError("Subclasses must implement this method")