from langgraph.runtime import Runtime
from ..agent_base import AgentBase
from typing import Any, List, Callable, Annotated
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver
from app.models.customer import CustomerModel
from langgraph.store.postgres import PostgresStore
from app.api.routes import AgentRunRequest
from app.models.conversation import CallContext
from app.services.agent_registry import register_agent

import uuid

class CustomerSupportAgentState(BaseModel):
  messages: Annotated[list, add_messages]

@register_agent("customer_support_agent")
class CustomerSupportAgent(AgentBase):
  def __init__(self, system_prompt: str, embedding_model: Any, llm: Any, tools: List[Callable], db_uri: str):
    super().__init__()
    self.system_prompt = system_prompt
    self.llm = llm
    self.tools = tools
    self.llm_with_tools = self.llm.bind_tools(self.tools)
    self.tool_node = ToolNode(self.tools)
    self.embedding_model = embedding_model
    self.db_uri = db_uri
    with PostgresStore.from_conn_string(
      conn_string = self.db_uri,
    ) as store:
      store.setup()
      self.agent = self.build_graph().compile(checkpointer=InMemorySaver(), store=store)

  def run(self, request: AgentRunRequest, context: CallContext, customer: CustomerModel) -> str:
    response = self.agent.invoke({
      "messages": [HumanMessage(content=request.request)],    
    }
    , config={"configurable": {"thread_id": f"Customer_Support_Agent_{context.call_sid}"}}
    , context=customer
    )
    return response.content

  async def agent(self, state: CustomerSupportAgentState, runtime: Runtime[CustomerModel]) -> CustomerSupportAgentState:
    customerId = runtime.context.id
    namespace = ("Instruction", "CustomerSupportAgent")
    instruction = runtime.store.get(namespace, customerId)
    messages = [SystemMessage(content=self.system_prompt.format(learned_instruction = instruction))] + state.messages
    response = self.llm_with_tools.invoke(messages)
    return {
      "messages": [response]
    }

  async def routing(self, state: CustomerSupportAgentState):
    if state.messages[-1].tool_calls:
      return "tool"
    else:
      return END

  def build_graph(self) -> StateGraph:
    graph = StateGraph(CustomerSupportAgentState, context_schema=CustomerModel)
    graph.add_node("agent", self.agent)
    graph.add_node("tool_node", self.tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
      "agent",
      self.routing,
      {
        "tool": "tool_node",
        END: END
      }
    )
    
    return graph