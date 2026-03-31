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
from src.services.tool_registry import get_tools

from src.core.customer import CustomerModel
from langgraph.store.postgres import PostgresStore
from src.core.agent_run_request_model import AgentRunRequest

from dotenv import load_dotenv
from datetime import datetime
from src.services.skill_registry import SkillRecord, get_skills, get_skill_tools
from langchain.tools import InjectedState, tool
from langgraph.types import Command
load_dotenv()

class AgentState(BaseModel):
  messages: Annotated[list, add_messages]
  skills: dict[str, SkillRecord]
  session_id: str
  customer_id: str

class AgentFactory(AgentBase):
  def __init__(self, system_prompt: str, name: str, llm: Any, tools: List[str], db_uri: str, skill_names: List[str]):
    super().__init__()
    self.system_prompt = system_prompt
    self.name = name
    self.llm = llm
    self.skill_names = skill_names
    self.base_tools = get_tools(tools) + [self.remove_thread_id]
    self.toolNode = ToolNode(self.base_tools + get_skill_tools(self.skill_names))
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

  async def arun(self, request: AgentRunRequest, customer: CustomerModel, session_id: str) -> str:
    """Run the graph with async tool support (await ainvoke). Use from FastAPI/async code."""
    thread_id = f"{self.name}:{customer.id}"
    config = {"configurable": {"thread_id": thread_id}}

    existing_state = self.support_agent.get_state(config=config)
    has_existing_state = existing_state is not None and bool(existing_state.values)

    if not has_existing_state:
      # New conversation - initialize with full state
      result = await self.support_agent.ainvoke(
        {
          "messages": [HumanMessage(content=request.request)],
          "skills": get_skills(self.skill_names),
          "session_id": session_id,
          "customer_id": customer.id
        },
        config=config,
        context=customer,
      )
    else:
      # Continuing existing conversation
      # Check if there's a pending tool call that needs to be handled first
      messages = existing_state.values.get("messages", [])
      if messages and hasattr(messages[-1], "tool_calls") and messages[-1].tool_calls:
        # Last message has pending tool calls - let the graph handle them first
        # by invoking without new messages (will route to tool_node, then back to agent)
        result = await self.support_agent.ainvoke(
          None,  # No new input, let graph continue from checkpoint
          config=config,
          context=customer,
        )
      else:
        # No pending tool calls - safe to add new user message
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

  async def tool_node(self, state: AgentState) -> dict:
    """Execute tools and return ToolMessage responses.

    The ToolNode automatically creates ToolMessage responses with proper tool_call_id
    for each tool call in the last assistant message.
    """
    try:
      response = await self.toolNode.ainvoke(state)
      print(response)
      # ToolNode returns a list of ToolMessage objects
      return response
    except Exception as e:
      # If tool execution fails, return error as tool response
      import logging
      logger = logging.getLogger(__name__)
      logger.error(f"Tool execution failed: {e}")
      # Return a placeholder - in production you might want to create a ToolMessage with error
      raise

  @tool  
  # remove the thread_id from the short term memory. It is called when the call is ended. Also we will called when user request to reset the conversation.
  async def remove_thread_id(self, state: Annotated[BaseModel, InjectedState]) -> None:
    """Remove the thread_id from the short term memory. It is called when the call is ended. Also we will called when user request to reset the conversation."""
    thread_id = f"Customer_Support_Agent:{state.customer_id}"
    self.checkpointer.delete(thread_id)

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

  def agent(self, state: AgentState, runtime: Runtime[CustomerModel]) -> AgentState:
    customerId = runtime.context.id
    namespace = ("my_intelligence", self.name)
    intelligence = runtime.store.get(namespace, customerId)
    skills = state.skills

    # Build system message with context
    system_msg = SystemMessage(content=self.system_prompt.format(
      learned_instruction=intelligence,
      current_date=datetime.now().strftime("%Y-%m-%d"),
      customer_info=runtime.context.model_dump_json(),
      available_skills=json.dumps([{"name": skill.name, "description": skill.description} for skill in skills.values() if not skill.active]),
      active_skills=json.dumps([{"name": skill.name, "body": skill.body} for skill in skills.values() if skill.active])
    ))

    # Prepend system message to existing conversation
    messages = [system_msg] + state.messages

    # Get active skill tools for this turn
    skill_tools = get_skill_tools([skill.name for skill in skills.values() if skill.active])

    # Bind tools and invoke - this may produce tool_calls
    response = self.llm.bind_tools(self.base_tools + skill_tools).invoke(messages)

    return {
      "messages": [response]
    }

  def routing(self, state: AgentState):
    if state.messages[-1].tool_calls:
      return "tool"
    else:
      return END

  def build_graph(self) -> StateGraph:
    graph = StateGraph(AgentState, context_schema=CustomerModel)
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