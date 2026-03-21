# Agent dispatch — high-level orchestration for customer service conversations
import json
import logging
from typing import Any, Optional, Type

from app.models.conversation import CallContext
from app.infrastructure.redis import get_call_state, set_call_state, delete_call_state
from app.services.agent_registry import AgentType, get_agent_registry
from app.api.routes import AgentRunRequest

logger = logging.getLogger(__name__)

_agents_pkg_loaded = False


def ensure_agents_loaded() -> None:
    """Import `agents` once so `@register_agent` modules run and populate the registry."""
    global _agents_pkg_loaded
    if _agents_pkg_loaded:
        return
    _agents_pkg_loaded = True
    try:
        import agents  # noqa: F401
    except ImportError:
        logger.debug("agents package not importable; agent registry may stay empty")

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


async def initialize_call(
    call_sid: str,
    from_number: str,
    to_number: str,
    customer_data: Optional[dict] = None,
    active_agent: Optional[str] = None,
) -> None:
    """
    Initialize call state in Redis when a call starts.
    
    This sets up the conversation context that persists throughout the call,
    enabling fast lookups and maintaining conversation state.

    `active_agent` is the logical name registered with `@register_agent` for this call.
    """
    ensure_agents_loaded()
    if active_agent is not None and active_agent not in get_agent_registry():
        logger.warning(
            "active_agent %r is not in the registry (known: %s)",
            active_agent,
            ", ".join(get_agent_registry().names()) or "(none)",
        )

    initial_state = {
        "call_sid": call_sid,
        "from_number": from_number,
        "to_number": to_number,
        "conversation_history": [],
        "extracted_entities": {},  # order_id, customer_id, etc.
        "pending_actions": [],
        "customer_data": customer_data or {},
        "started_at": None,  # Will be set by caller
        "active_agent": active_agent,
    }
    
    await set_call_state(call_sid, json.dumps(initial_state), ttl_seconds=CALL_STATE_TTL)
    logger.info(f"Call initialized: {call_sid} from {from_number}")

def invoke_agent(request: AgentRunRequest, context: CallContext) -> str:
    """Invoke an agent with the given parameters, request, and context."""
    ensure_agents_loaded()
    agent_class = get_registered_agent_class(request.agent_name)
    if not agent_class:
        raise ValueError(f"Agent {request.agent_name} not found")
    return agent_class.run(request, context)

def get_registered_agent_class(name: str) -> Optional[AgentType]:
    """Return the agent class for a registry name, or None if unknown."""
    ensure_agents_loaded()
    return get_agent_registry().get(name)


async def get_active_agent_class(call_sid: str) -> Optional[AgentType]:
    """Resolve the agent class for this call from Redis state, if `active_agent` was set."""
    ensure_agents_loaded()
    ctx = await get_conversation_context(call_sid)
    if not ctx:
        return None
    name = ctx.get("active_agent")
    if not name:
        return None
    return get_agent_registry().get(name)


async def get_conversation_context(call_sid: str) -> Optional[dict]:
    """
    Retrieve current conversation state from Redis.
    
    Returns None if call not found (expired or never initialized).
    """
    state_json = await get_call_state(call_sid)
    if state_json:
        return json.loads(state_json)
    return None


async def update_conversation_context(call_sid: str, updates: dict) -> None:
    """
    Merge updates into existing conversation state.
    
    Preserves existing data while applying new values.
    """
    current = await get_conversation_context(call_sid)
    if not current:
        logger.warning(f"Attempted to update non-existent call state: {call_sid}")
        return
    
    # Deep merge for nested dicts
    for key, value in updates.items():
        if isinstance(value, dict) and key in current and isinstance(current[key], dict):
            current[key].update(value)
        else:
            current[key] = value
    
    await set_call_state(call_sid, json.dumps(current), ttl_seconds=CALL_STATE_TTL)


async def append_to_history(call_sid: str, role: str, content: str) -> None:
    """
    Add a message to the conversation history.
    
    role: "user", "agent", "system", "tool_result"
    """
    current = await get_conversation_context(call_sid)
    if not current:
        return
    
    current["conversation_history"].append({
        "role": role,
        "content": content,
    })
    
    # Keep only last 20 messages to prevent Redis bloat
    if len(current["conversation_history"]) > 20:
        current["conversation_history"] = current["conversation_history"][-20:]
    
    await set_call_state(call_sid, json.dumps(current), ttl_seconds=CALL_STATE_TTL)


async def extract_and_store_entities(call_sid: str, text: str) -> dict:
    """
    Extract key entities from user text and store in conversation state.
    
    Looks for: phone numbers, order IDs, email addresses, customer names, etc.
    Returns extracted entities.
    """
    import re
    
    entities = {}
    
    # Order ID patterns (ORD-123, #12345, etc.)
    order_patterns = [
        r'(?:order|ord)[\s#-]*([A-Z0-9-]+)',
        r'#(\d{5,10})',
        r'(?:ticket|case)[\s#-]*([A-Z0-9-]+)',
    ]
    for pattern in order_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            entities["order_id"] = match.group(1)
            break
    
    # Email pattern
    email_match = re.search(r'[\w.-]+@[\w.-]+\.\w+', text)
    if email_match:
        entities["email"] = email_match.group(0)
    
    # Phone pattern (simple)
    phone_match = re.search(r'\+?1?\s*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    if phone_match:
        entities["phone"] = phone_match.group(0)
    
    # Store extracted entities
    if entities:
        await update_conversation_context(call_sid, {"extracted_entities": entities})
        logger.info(f"Entities extracted for {call_sid}: {entities}")
    
    return entities


# ═══════════════════════════════════════════════════════════════════════════════
# Call Lifecycle Management
# ═══════════════════════════════════════════════════════════════════════════════

async def end_call(call_sid: str, persist_data: bool = True) -> None:
    """
    Clean up call state when conversation ends.
    
    If persist_data is True, sync any pending updates to PostgreSQL before deletion.
    """
    conv_context = await get_conversation_context(call_sid)
    
    if conv_context and persist_data:
        # TODO: Sync any pending updates to PostgreSQL
        # customer_data = conv_context.get("customer_data", {})
        # if customer_data.get("modified"):
        #     await update_customer_in_db(customer_data)
        logger.info(f"Persisting call data for {call_sid}")
    
    await delete_call_state(call_sid)
    logger.info(f"Call ended and state cleaned up: {call_sid}")


async def get_call_summary(call_sid: str) -> str:
    """
    Generate a summary of the call for human agents or logging.
    """
    conv_context = await get_conversation_context(call_sid)
    if not conv_context:
        return f"No context found for call {call_sid}"
    
    history = conv_context.get("conversation_history", [])
    entities = conv_context.get("extracted_entities", {})
    
    summary_parts = [
        f"Call {call_sid}",
        f"From: {conv_context.get('from_number', 'unknown')}",
        f"Exchanges: {len(history)}",
    ]
    
    if entities:
        summary_parts.append(f"Entities: {json.dumps(entities)}")
    
    if conv_context.get("pending_actions"):
        summary_parts.append(f"Pending: {len(conv_context['pending_actions'])} actions")
    
    return " | ".join(summary_parts)
