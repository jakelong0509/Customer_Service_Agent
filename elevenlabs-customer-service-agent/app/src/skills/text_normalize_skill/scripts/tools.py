"""
Abbreviation store/retrieve tools using LangChain long-term memory.
Use a store with put/get (e.g. langgraph.store.memory.InMemoryStore) when building the agent
for namespace-based persistence. For production, use a DB-backed store (e.g. PostgresStore).
"""
from langchain.tools import tool, InjectedStore
from typing_extensions import Annotated
from typing import Any, Literal
from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId
from langgraph.types import Command, Send
from typing import List, Callable
from src.agents.rxnorm_mapping_agent.state import NormalizedText
from pydantic import BaseModel
from langchain.tools import InjectedState

# Namespace for long-term memory (LangGraph store API). Groups all abbreviation entries.
ABBREVIATIONS_NAMESPACE = ("rxnorm_mapping_agent", "abbreviations")


def _norm(s: str) -> str:
  return (s or "").strip()


@tool
def store_abbreviations(
  abbr_acr: str,
  use_context: str,
  meaning: str,
  store: Annotated[Any, InjectedStore],
):
  """
  Store MEDIUM and LOW confident clinical abbreviations and acronyms from medical notes
  in long-term memory (namespace-based store).

  Parameters:
  abbr_acr: the clinical abbreviation or acronym written in the medical note
  use_context: the context of the abbreviation or acronym used in the medical note
  meaning: the true meaning of the abbreviation and/or acronym
  """
  try:
    key, val, use_context = _norm(abbr_acr), _norm(meaning), _norm(use_context)
    if not key or not val:
      return "Fail to store: abbreviation and meaning must be non-empty."
    if not use_context:
      return "Fail to store: use_context must be non-empty."
    # LangGraph long-term memory: put(namespace, key, value)
    if hasattr(store, "put"):
      store.put(ABBREVIATIONS_NAMESPACE, key, {"meaning": val, "use_context": use_context})
      return f"Stored: '{key}' -> '{val}'"
    # Fallback: langchain_core flat store (mset)
    if hasattr(store, "mset"):
      composite_key = f"{ABBREVIATIONS_NAMESPACE[0]}::{key}"
      store.mset([(composite_key, {"meaning": val, "use_context": use_context})])
      return f"Stored: '{key}' -> '{val}'"
    store[key] = {"meaning": val, "use_context": use_context  }
    return f"Stored: '{key}' -> '{val}'"
  except Exception as e:
    return f"Fail to store abbreviations due to error: {e}"


@tool
def retrieve_abbreviations(
  abbr_acr: str,
  store: Annotated[Any, InjectedStore],
):
  """
  Retrieve the meaning of a clinical abbreviation or acronym from long-term memory.

  Parameters:
  abbr_acr: the clinical abbreviation or acronym to look up
  """
  try:
    key = _norm(abbr_acr)
    if not key:
      return None

    # LangGraph BaseStore API: get(namespace, key)
    if hasattr(store, "get") and callable(getattr(store, "get")):
      result = store.get(ABBREVIATIONS_NAMESPACE, key)
      if result is None:
        return None
      value = result.value if hasattr(result, "value") else result
      if isinstance(value, dict):
        meaning = value.get("meaning")
        use_context = value.get("use_context")
        return f"Meaning: {meaning} \n Use context: {use_context}" if meaning else None
      return f"Stored value: {value}"

    # Fallback: dict-like store interface
    if hasattr(store, "mget"):
      composite_key = f"{ABBREVIATIONS_NAMESPACE[0]}::{key}"
      results = store.mget([composite_key])
      if results and results[0]:
        value = results[0]
        if isinstance(value, dict):
          return f"Meaning: {value.get('meaning')} \n Use context: {value.get('use_context')}"
        return str(value)
      return None

    # Last resort: direct key access
    value = store.get(key)
    if isinstance(value, dict):
      return f"Meaning: {value.get('meaning')} \n Use context: {value.get('use_context')}"
    return str(value) if value else None

  except Exception as e:
    return f"Fail to retrieve abbreviations due to error: {e}"

@tool
def reflection(original_note: str, normalized_note: str):
  """
  Reflect on the original note and the normalized note, making sure that all the abbreviations are correctly handled.
  Parameters:
  original_note: the original note
  normalized_note: the normalized note
  """
  message = f"Original note: {original_note}\nNormalized note: {normalized_note}"
  return message

# @tool
# def handoff_to_agent(normalized_note: str, agent_name: Literal["clinical_entity_extraction"], tool_call_id: Annotated[str, InjectedToolCallId]):
#   """
#   Hand off the normalized note to the specified agent.
#   Parameters:
#   normalized_note: the normalized note
#   agent_name: the name of the agent to hand off to (RxNorm or clinical_entity_extraction)
#   tool_call_id: the tool call id
#   """
#   update = {
#     "global_medical_state": {
#       "normalized_note": normalized_note,
#       "extracted_entities": [],
#       "resolved_relationship": []
#     },
#     "messages": [
#       ToolMessage(
#         name = f"handoff_to_{agent_name}_agent",
#         content = f"Successfully handed off to {agent_name} agent",
#         tool_call_id = tool_call_id
#       )
#     ]
#   }
#   return Command(
#     update = update,
#     goto = f"handoff_to_{agent_name}_agent"
#   )

@tool
async def normalize_text(normalized_text: NormalizedText, state: Annotated[BaseModel, InjectedState], tool_call_id: Annotated[str, InjectedToolCallId]) -> NormalizedText:
  """
  Normalize the text.
  Parameters:
  normalized_text: the normalized text
  """
  normalized_text = NormalizedText(normalized_text=normalized_text.normalized_text)
  update = {
    "messages": [ToolMessage(content=f"Normalized text: {normalized_text.normalized_text}", tool_call_id=tool_call_id)],
    "normalized_text": normalized_text
  }
  return Command(
    update=update
  )


TOOLS = [store_abbreviations, retrieve_abbreviations, normalize_text]
def get_tools() -> List[Callable]:
    return TOOLS