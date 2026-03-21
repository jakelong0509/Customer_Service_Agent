# CRM lookups, account info
from app.models.conversation import CallContext


async def lookup_customer(arguments: dict, context: CallContext) -> str:
    """Look up customer by phone (or id). Returns summary for the agent to speak."""
    phone = arguments.get("phone") or arguments.get("phone_number") or context.from_number
    customer_id = arguments.get("customer_id")
    # TODO: use app.infrastructure.database to query; for now stub
    if customer_id:
        return f"Customer ID {customer_id}: found (stub)."
    if phone:
        return f"Customer with phone {phone}: found (stub)."
    return "No phone or customer_id provided."

async def get_account_info(arguments: dict, context: CallContext) -> str:
    """Get account status, plan, or subscription for the current caller."""
    # TODO: resolve caller from context.from_number, then DB lookup
    return f"Account for {context.from_number}: active, standard plan (stub)."
