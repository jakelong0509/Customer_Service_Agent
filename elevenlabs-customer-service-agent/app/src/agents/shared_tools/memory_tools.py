from langchain.tools import tool, InjectedStore, InjectedState
from typing import Annotated, Any, Literal
from pydantic import BaseModel
from langgraph.store.postgres import PostgresStore
from datetime import datetime
from src.services.agent_registry import get_agent_names
from src.services.tool_registry import register_tool

# Must be non-empty so Literal[*agent_list] is valid for LangChain tool schema (not Literal[()]).
_agent_names = get_agent_names()
agent_list = _agent_names if _agent_names else ["_no_agent_configured"]


@tool
@register_tool("retrieve_conversation_history")
async def retrieve_conversation_history(agent_name: str, store: Annotated[PostgresStore, InjectedStore], state: Annotated[BaseModel, InjectedState]) -> str: # type: ignore
  """
  Retrieve the conversation history for a customer
  Args:
    agent_name: str - The name of the agent
  Returns:
    str: The conversation history
  """
  if agent_name not in agent_list:
    return f"Error: Agent {agent_name} not found, please use one of the following agents: {agent_list}"
  try:
    namespace = (agent_name, "conversation_history")
    # As per langchain documentation, langchain automatically sort the memory by updated_at DESC 
    conversation_history = store.get(namespace, key = state.customer.id)
    return conversation_history.get("conversation_history")
  except Exception as e:
    return f"Error: {e}"

@tool
@register_tool("store_conversation_history")
async def store_conversation_history(agent_name: str, conversation_history_summarized: str, store: Annotated[PostgresStore, InjectedStore], state: Annotated[BaseModel, InjectedState]) -> str: # type: ignore
  """
  Store the conversation history for a customer
  Args:
    agent_name: str - The name of the agent
    conversation_history_summarized: str - The summarized conversation history
  Returns:
    str: The conversation history
  """
  if agent_name not in agent_list:
    return f"Error: Agent {agent_name} not found, please use one of the following agents: {agent_list}"
  try:
    namespace = (agent_name, "conversation_history")
    store.put(namespace, key = state.customer.id, value = {"conversation_history": conversation_history_summarized})
    return f"Conversation history stored for customer {state.customer.id}"
  except Exception as e:
    return f"Error: {e}"

@tool
@register_tool("updating_internal_cognition")
async def updating_internal_cognition(agent_name: str, internal_cognition: str, store: Annotated[PostgresStore, InjectedStore], state: Annotated[BaseModel, InjectedState]) -> str: # pyright: ignore[reportInvalidTypeForm]
  """
  Updating the internal cognition of the agent
  Args:
    agent_name: str - The name of the agent
    internal_cognition: str - The internal cognition of the agent
  Returns:
    str: The internal cognition of the agent
  """
  if agent_name not in agent_list:
    return f"Error: Agent {agent_name} not found, please use one of the following agents: {agent_list}"
  try:
    namespace = (agent_name,)
    store.put(namespace, key = "internal_cognition", value = {"internal_cognition": internal_cognition})
    return f"Internal cognition updated for agent {agent_name}"
  except Exception as e:
    return f"Error: {e}"

@tool
@register_tool("retrieving_internal_cognition")
async def retrieving_internal_cognition(agent_name: str, store: Annotated[PostgresStore, InjectedStore], state: Annotated[BaseModel, InjectedState]) -> str: # type: ignore
  """
  Retrieving the internal cognition of the agent
  Args:
    agent_name: str - The name of the agent
  Returns:
    str: The internal cognition of the agent
  """
  if agent_name not in agent_list:
    return f"Error: Agent {agent_name} not found, please use one of the following agents: {agent_list}"
  try:
    namespace = (agent_name,)
    internal_cognition = store.get(namespace, key = "internal_cognition")
    return internal_cognition.get("internal_cognition")
  except Exception as e:
    return f"Error: {e}"

@tool
@register_tool("store_session_outcome")
async def store_session_outcome(
  agent_name: str, # type: ignore
  user_intent: str,
  skills_used: list[str],
  outcome: Literal["resolved", "escalated", "failed", "incomplete"],
  key_learnings: list[str],
  store: Annotated[Any, InjectedStore],
  state: Annotated[BaseModel, InjectedState]
) -> str:
  """
  Store a structured session outcome with key learnings for future pattern matching.
  Use this at the end of a conversation to capture what happened and what was learned.

  Args:
    agent_name: The name of the agent that handled the session
    user_intent: Classified intent (e.g., "refund_request", "billing_inquiry", "technical_issue")
    skills_used: List of skill names that were invoked during the session
    outcome: The final outcome of the session
    key_learnings: Specific lessons learned from this interaction (e.g., "Policy X applies to refunds within 30 days", "Always verify email before sending")

  Returns:
    str: Confirmation that the session outcome was stored
  """
  if agent_name not in agent_list:
    return f"Error: Agent {agent_name} not found, please use one of the following agents: {agent_list}"
  try:
    namespace = (agent_name, "session_outcomes", state.session_id)
    session_data = {
      "customer_id": state.customer.id,
      "session_id": state.session_id,
      "user_intent": user_intent,
      "skills_used": skills_used,
      "outcome": outcome,
      "key_learnings": key_learnings,
      "timestamp": store.get(("system", "current_time")) if store.get(("system", "current_time")) else "unknown"
    }
    store.set(namespace, key = state.customer.id, value = session_data)
    return f"Session outcome stored for customer {state.customer.id}, session {state.session_id}"
  except Exception as e:
    return f"Error: {e}"

@tool
@register_tool("find_similar_sessions")
async def find_similar_sessions(
  agent_name: str, # type: ignore
  user_intent: str,
  outcome_filter: Literal["resolved", "escalated", "failed", "any"],
  store: Annotated[Any, InjectedStore]
) -> list[dict]:
  """
  Find past sessions with similar intent to learn from previous approaches.
  Use this when starting a new conversation to see what worked before.

  Args:
    agent_name: The name of the agent to search within
    user_intent: The intent to match against (e.g., "refund_request")
    outcome_filter: Filter by outcome type, or "any" for all outcomes

  Returns:
    list: Up to 5 similar sessions with their learnings and outcomes
  """
  if agent_name not in agent_list:
    return f"Error: Agent {agent_name} not found, please use one of the following agents: {agent_list}"
  try:
    # Search all session outcomes for this agent
    all_sessions = store.search((agent_name, "session_outcomes"), limit=100)

    # Filter by intent and outcome
    matching = []
    for session in all_sessions:
      if session.get("user_intent") == user_intent:
        if outcome_filter == "any" or session.get("outcome") == outcome_filter:
          matching.append({
            "session_id": session.get("session_id"),
            "outcome": session.get("outcome"),
            "skills_used": session.get("skills_used"),
            "key_learnings": session.get("key_learnings")
          })

    # Return up to 5 most recent matches
    return matching[:5]
  except Exception as e:
    return [{"error": str(e)}]