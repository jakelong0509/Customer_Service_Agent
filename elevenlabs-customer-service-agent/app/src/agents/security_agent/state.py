from pydantic import Field
from src.core.agent_state import AgentState


class SecurityAgentState(AgentState):
    """State for the security agent.

    Extends base state with fields for attachment scanning and conversation context.
    These map directly to the {attachment_metadata} and {conversation_context}
    placeholders in the security agent system prompt.
    """
    attachment_metadata: dict = Field(default_factory=dict)
    threat_level: str = "unknown"
    conversation_context: str = ""
