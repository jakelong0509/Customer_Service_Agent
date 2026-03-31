# Agent dispatch — high-level orchestration for customer service conversations
import json
import logging
from typing import Any, Optional, Type

from src.core.conversation import CallContext
from src.infrastructure.redis import get_call_state, set_call_state, delete_call_state
from src.services.agent_registry import AgentType, get_agent_registry
from src.core.agent_run_request_model import AgentRunRequest
from src.services.agent_registry import get_agent
from src.core.customer import CustomerModel
logger = logging.getLogger(__name__)

_agents_pkg_loaded = False


# def ensure_agents_loaded() -> None:
#     """Import `agents` once so `@register_agent` modules run and populate the registry."""
#     global _agents_pkg_loaded
#     if _agents_pkg_loaded:
#         return
#     _agents_pkg_loaded = True
#     try:
#         import agents  # noqa: F401
#     except ImportError:
#         logger.debug("agents package not importable; agent registry may stay empty")

# Maximum time to keep call state in Redis (1 hour)
CALL_STATE_TTL = 3600


class AgentResponse:
    """Structured response from the agent dispatch layer."""
    
    def __init__(
        self,
        content: str,
        action_type: str = "response",
        requires_followup: bool = False,
        async_job_id: Optional[str] = None,
        suggested_tools: Optional[list] = None,
    ):
        self.content = content
        self.action_type = action_type  # "response", "tool_call", "handoff", "async_pending"
        self.requires_followup = requires_followup
        self.async_job_id = async_job_id
        self.suggested_tools = suggested_tools or []
    
    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "action_type": self.action_type,
            "requires_followup": self.requires_followup,
            "async_job_id": self.async_job_id,
            "suggested_tools": self.suggested_tools,
        }


# async def initialize_call(
#     call_sid: str,
#     from_number: str,
#     customer_data: Optional[dict] = None,
#     active_agent: Optional[str] = None,
# ) -> None:
#     """
#     Initialize call state in Redis when a call starts.
    
#     This sets up the conversation context that persists throughout the call,
#     enabling fast lookups and maintaining conversation state.

#     `active_agent` is the logical name registered with `@register_agent` for this call.
#     """
#     ensure_agents_loaded()
#     if active_agent is not None and active_agent not in get_agent_registry():
#         logger.warning(
#             "active_agent %r is not in the registry (known: %s)",
#             active_agent,
#             ", ".join(get_agent_registry().names()) or "(none)",
#         )

#     initial_state = {
#         "call_sid": call_sid,
#         "caller_number": from_number,
#         "customer_data": customer_data or {},
#         "started_at": None,  # Will be set by caller
#         "active_agent": active_agent,
#     }
    
#     await set_call_state(call_sid, json.dumps(initial_state), ttl_seconds=CALL_STATE_TTL)
#     logger.info(f"Call initialized: {call_sid} from {from_number}")

async def invoke_agent(agent_name: str, request: AgentRunRequest, customer: CustomerModel, session_id: str) -> str:
    """Invoke an agent with the given parameters, request, and context."""
    agent = get_agent(agent_name)
    if not agent:
        raise ValueError(f"Agent {request.agent_name} not found")
    return await agent.arun(request, customer, session_id)


