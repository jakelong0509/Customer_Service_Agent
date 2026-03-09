# Tickets, refunds
from app.models.conversation import CallContext
from app.tools.registry import register


@register("create_ticket")
async def create_ticket(arguments: dict, context: CallContext) -> str:
    """Create a support ticket. Returns ticket id and summary."""
    subject = arguments.get("subject") or "Phone support"
    description = arguments.get("description") or ""
    # TODO: persist via DB; for now stub
    ticket_id = "TKT-stub-001"
    return f"Created ticket {ticket_id}: {subject}. We will follow up."


@register("check_refund_eligibility")
async def check_refund_eligibility(arguments: dict, context: CallContext) -> str:
    """Check if an order or account is eligible for refund."""
    order_id = arguments.get("order_id") or arguments.get("order")
    # TODO: business rules + DB; for now stub
    if order_id:
        return f"Order {order_id}: eligible for refund within 30 days (stub)."
    return "Please provide an order ID to check refund eligibility."


@register("request_refund")
async def request_refund(arguments: dict, context: CallContext) -> str:
    """Submit a refund request for an order."""
    order_id = arguments.get("order_id") or arguments.get("order")
    reason = arguments.get("reason") or ""
    # TODO: create refund request in DB, return confirmation
    if order_id:
        return f"Refund requested for order {order_id}. You will receive confirmation by email (stub)."
    return "Please provide an order ID to request a refund."
