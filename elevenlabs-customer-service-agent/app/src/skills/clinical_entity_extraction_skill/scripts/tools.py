from typing import Any, Literal, Annotated, List, Callable

from langchain.tools import tool
from langchain_core.tools import InjectedToolCallId
from langgraph.types import Command, Send
from langchain_core.messages import ToolMessage
from src.agents.rxnorm_mapping_agent.state import ExtractedEntities
from pydantic import BaseModel
from langchain.tools import InjectedState

@tool
async def extract_entities(extracted_entities: ExtractedEntities, state: Annotated[BaseModel, InjectedState], tool_call_id: Annotated[str, InjectedToolCallId]) -> ExtractedEntities:
  """
  Extract the entities from the text.
  Parameters:
  extracted_entities: the extracted entities
  """
  extracted_entities = ExtractedEntities(extracted_entities=extracted_entities.extracted_entities)
  update = {
    "messages": [ToolMessage(content=f"Entities extracted", tool_call_id=tool_call_id)],
    "extracted_entities": extracted_entities
  }
  return Command(
    update=update
  )

TOOLS = [extract_entities]
def get_tools() -> List[Callable]:
    return TOOLS