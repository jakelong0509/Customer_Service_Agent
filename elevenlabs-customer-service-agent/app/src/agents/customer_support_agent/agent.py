from __future__ import annotations

import asyncio
import os
import sys
import json

from typing import Any, Callable, List, Annotated, Literal

from langgraph.runtime import Runtime
from src.core.agent_base import AgentBase
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
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
from dotenv import load_dotenv
from src.services.agent_registry import AgentType, get_agent_registry
from datetime import datetime
from src.skills.skill_registry import SkillRecord, get_skills, get_skill_tools
from src.agents.shared_tools.skill_tools import activate_skill, deactivate_skill
from langchain_core.tools import tool
from langgraph.types import Command
load_dotenv()

class CustomerSupportAgentState(BaseModel):
  messages: Annotated[list, add_messages]
  skills: dict[str, SkillRecord]
  

@register_agent("customer_support_agent")
class CustomerSupportAgent(AgentBase):
  def __init__(self, system_prompt: str, llm: Any, tools: List[Callable], db_uri: str, type: Literal["voice", "chat", "email"], skill_names: List[str]):
    super().__init__()
    self.system_prompt = system_prompt
    self.llm = llm
    self.skill_names = skill_names
    self.base_tools = tools + [activate_skill, deactivate_skill]
    self.toolNode = ToolNode(self.base_tools + get_skill_tools(self.skill_names))
    self.type = type
    self.db_uri = db_uri
    # reload the skills by skill names, the skill objects include the tools and the skill body.
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
    thread_id = f"Customer_Support_Agent:{self.type}:{request.call_sid}"
    config = {"configurable": {"thread_id": thread_id}}
    
    existing_state = self.support_agent.get_state(config=config)
    has_existing_state = existing_state is not None and bool(existing_state.values)

    if not has_existing_state:
      result = await self.support_agent.ainvoke(
        {
          "messages": [HumanMessage(content=request.request)],
          "skills": get_skills(self.skill_names)
        },
        config=config,
        context=customer,
      )
    else:
       result = await self.support_agent.ainvoke(
        {
            "messages": [HumanMessage(content=request.request)]
        },
        config=config,
        context=customer,
      )
    return self._last_message_text(result)

  def run(self, request: AgentRunRequest, customer: CustomerModel) -> str:
    """Sync entrypoint for scripts/tests only. Prefer arun() inside an async app."""
    return asyncio.run(self.arun(request, customer))

  async def tool_node(self, state: CustomerSupportAgentState) -> dict:
    response = await self.toolNode.ainvoke(state)
    if isinstance(response, list) and isinstance(response[-1], Command):
      return response[-1]
    else:
      return Command(
        update = response,
        goto = "agent"
      )

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
    skills = state.skills
    messages = [SystemMessage(content=self.system_prompt.format(learned_instruction = instruction
    , current_date = datetime.now().strftime("%Y-%m-%d")
    , available_skills = json.dumps([{"name": skill.name, "description": skill.description} for skill in skills.values() if not skill.active])
    , active_skills = json.dumps([{"name": skill.name, "body": skill.body} for skill in skills.values() if skill.active])))] + state.messages
    # Get the active skills tools
    skill_tools = get_skill_tools([skill.name for skill in skills.values() if skill.active])
    # --------------------------------
    response = self.llm.bind_tools(self.base_tools + skill_tools).invoke(messages)
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
TOOLS = []
DB_URI = os.getenv("POSTGRES_CONNECTION_STRING")

_agent_voice: CustomerSupportAgent | None = None


def get_agent_voice() -> CustomerSupportAgent:
  """Lazy singleton so importing this module does not open Postgres (pytest collection, CI)."""
  global _agent_voice
  if _agent_voice is None:
    _agent_voice = CustomerSupportAgent(
      system_prompt=CUSTOMER_SUPPORT_SYSTEM_PROMPT,
      llm=LLM,
      tools=TOOLS,
      db_uri=DB_URI or "",
      type="voice",
      skill_names=["appointment_booking_skill"],
    )
  return _agent_voice
