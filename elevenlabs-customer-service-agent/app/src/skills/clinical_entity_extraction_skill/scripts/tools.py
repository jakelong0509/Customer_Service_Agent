from typing import Any, Literal, Annotated, List, Callable

from langchain.tools import tool
from langchain_core.tools import InjectedToolCallId
from langgraph.types import Command, Send
from langchain_core.messages import ToolMessage

TOOLS = []
def get_tools() -> List[Callable]:
    return TOOLS