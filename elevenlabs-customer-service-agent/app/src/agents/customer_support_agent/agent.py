from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Callable, List, Annotated, Literal

from langgraph.runtime import Runtime
from src.core.agent_base import AgentBase
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver
from pathlib import Path

from src.core.customer import CustomerModel
from langgraph.store.postgres import PostgresStore
from src.core.agent_run_request_model import AgentRunRequest
from src.core.conversation import CallContext
from src.services.agent_registry import register_agent
from langchain_openai import ChatOpenAI
from .tools import create_appointment
from dotenv import load_dotenv
from src.services.agent_registry import AgentType, get_agent_registry
from datetime import datetime
load_dotenv()

class CustomerSupportAgentState(BaseModel):
  messages: Annotated[list, add_messages]

@register_agent("customer_support_agent")
class CustomerSupportAgent(AgentBase):
  def __init__(self, system_prompt: str, llm: Any, tools: List[Callable], db_uri: str, type: Literal["voice", "chat", "email"]):
    super().__init__()
    self.system_prompt = system_prompt
    self.llm = llm
    self.tools = tools
    self.type = type
    self.llm_with_tools = self.llm.bind_tools(self.tools)
    self.tool_node = ToolNode(self.tools)
    self.db_uri = db_uri
    self.checkpointer = InMemorySaver()
    # from_conn_string is @contextmanager — the call returns a context manager, not PostgresStore.
    # __enter__() yields the real store; keep the CM alive so the DB connection stays open.
    if not self.db_uri:
      raise ValueError("db_uri (e.g. POSTGRES_CONNECTION_STRING) is required for PostgresStore")
    self._store_cm = PostgresStore.from_conn_string(conn_string=self.db_uri)
    self.store = self._store_cm.__enter__()
    try:
      self.store.setup()
      self.support_agent = self.build_graph().compile(
        checkpointer=self.checkpointer,
        store=self.store,
      )
    except BaseException:
      self._store_cm.__exit__(*sys.exc_info())
      raise

  def close(self) -> None:
    if getattr(self, "_store_cm", None) is not None:
      self._store_cm.__exit__(None, None, None)
      self._store_cm = None

  async def arun(self, request: AgentRunRequest, customer: CustomerModel) -> str:
    """Run the graph with async tool support (await ainvoke). Use from FastAPI/async code."""
    result = await self.support_agent.ainvoke(
      {"messages": [HumanMessage(content=request.request)]},
      config={"configurable": {"thread_id": f"Customer_Support_Agent:{self.type}:{request.call_sid}"}},
      context=customer,
    )
    return self._last_message_text(result)

  def run(self, request: AgentRunRequest, customer: CustomerModel) -> str:
    """Sync entrypoint for scripts/tests only. Prefer arun() inside an async app."""
    return asyncio.run(self.arun(request, customer))

  @staticmethod
  def _last_message_text(result: dict) -> str:
    messages = result.get("messages", [])
    if not messages:
      return ""
    last = messages[-1]
    content = getattr(last, "content", None)
    if isinstance(content, str):
      return content
    if content is not None:
      return str(content)
    return str(last)

  def agent(self, state: CustomerSupportAgentState, runtime: Runtime[CustomerModel]) -> CustomerSupportAgentState:
    customerId = runtime.context.id
    namespace = ("Instruction", "CustomerSupportAgent")
    instruction = runtime.store.get(namespace, customerId)
    messages = [SystemMessage(content=self.system_prompt.format(learned_instruction = instruction, current_date = datetime.now().strftime("%Y-%m-%d")))] + state.messages
    response = self.llm_with_tools.invoke(messages)
    return {
      "messages": [response]
    }

  def routing(self, state: CustomerSupportAgentState):
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
    graph.add_edge("tool_node", "agent")

    return graph
  
  # remove the thread_id from the short term memory. It is called when the call is ended. Also we will called when user request to reset the conversation.
  def remove_thread_id(self, thread_id: str) -> None:
    self.checkpointer.delete(thread_id)


_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent / "system_prompt.md"
CUSTOMER_SUPPORT_SYSTEM_PROMPT = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
LLM = ChatOpenAI(model="kimi-k2.5", base_url="https://api.moonshot.ai/v1", temperature=0.6, max_tokens=25000, timeout=None, max_retries=2, extra_body={
        "thinking": {"type": "disabled"}
    })  # Pass additional request body via extra_body parameter to disable thinking
TOOLS = [create_appointment]
DB_URI = os.getenv("POSTGRES_CONNECTION_STRING")

agent_voice = CustomerSupportAgent(
  system_prompt=CUSTOMER_SUPPORT_SYSTEM_PROMPT,
  llm=LLM,
  tools=TOOLS,
  db_uri=DB_URI,
  type="voice"
)

