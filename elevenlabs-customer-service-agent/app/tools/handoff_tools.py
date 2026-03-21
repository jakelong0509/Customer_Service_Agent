# Human transfer
from app.models.conversation import CallContext


async def transfer_to_agent(arguments: dict, context: CallContext) -> str:
    """Request transfer to a human agent. Returns instruction for the agent to speak."""
    department = arguments.get("department") or arguments.get("queue") or "general"
    # Transfer is configured on Twilio dashboard (e.g. webhook to queue); this returns copy for the agent to speak.
    return f"Transfer to {department} requested. Please hold while we connect you (stub)."

async def schedule_callback(arguments: dict, context: CallContext) -> str:
    """Schedule a callback from an agent."""
    when = arguments.get("when") or arguments.get("time") or "next available"
    # TODO: create callback in queue/CRM
    return f"Callback scheduled for {when}. We will call you at {context.from_number} (stub)."
