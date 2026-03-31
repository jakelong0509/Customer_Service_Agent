
from typing import Annotated
from langchain.tools import InjectedState, tool, InjectedToolCallId
from pydantic import BaseModel
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from src.services.tool_registry import register_tool

@tool
@register_tool("activate_skill")
async def activate_skill(
  skill_name: str
  , state: Annotated[BaseModel, InjectedState]
  , tool_call_id: Annotated[str, InjectedToolCallId]
  ) -> str:
  """Activate a skill by name. The skill will be looked up from the conversation state.
  
  Args:
    skill_name: The name of the skill to activate (e.g., "appointment-booking")
  """
  skills = state.skills
  skill = skills[skill_name]
  if skill:
    skill.active = True
    return Command(update={"messages": [ToolMessage(content="Skill activated", tool_call_id=tool_call_id)], "skills": skills})
  return f"Skill '{skill_name}' not found"

@tool
@register_tool("deactivate_skill")
async def deactivate_skill(skill_name: str
, state: Annotated[BaseModel, InjectedState]
, tool_call_id: Annotated[str, InjectedToolCallId]
) -> str:
  """Deactivate a skill by name. The skill will be looked up from the conversation state.
  
  Args:
    skill_name: The name of the skill to deactivate (e.g., "appointment-booking")
  """
  skills = state.skills
  skill = skills[skill_name]
  if skill:
    skill.active = False
    return Command(update={"messages": [ToolMessage(content="Skill deactivated", tool_call_id=tool_call_id)], "skills": skills})
  return f"Skill '{skill_name}' not found"
