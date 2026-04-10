from typing import Annotated
from pydantic import BaseModel
from langgraph.graph.message import add_messages
from src.services.skill_registry import SkillRecord
from src.core.customer import CustomerModel


class AgentState(BaseModel):
    """Base state shared by all agents.

    Per-agent states subclass this and add their own fields.
    AgentFactory.build_graph() uses self.state_class so each agent's
    graph is typed to its specific state.
    """
    messages: Annotated[list, add_messages]
    skills: dict[str, SkillRecord]
    session_id: str
    customer: CustomerModel
