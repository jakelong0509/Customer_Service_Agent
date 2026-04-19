# HTTP routes — health and tool API for SendGrid Inbound Parse webhook
import logging
import json
import re
import pika
from typing import Optional, Any

from fastapi import APIRouter, BackgroundTasks, Form

from src.services.dispatch_agent import invoke_agent
from src.core.agent_run_request_model import SendGridInboundRequest
from src.services.rabbitmq_service import RabbitMQService
from fastapi.responses import Response
from src.core.customer import CustomerModel
from DAL.customerDA import CustomerDA

router = APIRouter(prefix="/api/sendgrid", tags=["api"])
logger = logging.getLogger(__name__)


def extract_message_id(headers: str | None) -> str | None:
    """Extract Message-ID from raw email headers."""
    if not headers:
        return None
    # Message-ID format: <unique-id@domain.com>
    match = re.search(r'Message-ID:\s*<([^>]+)>', headers, re.IGNORECASE)
    if match:
        return f"<{match.group(1)}>"
    # Try without angle brackets
    match = re.search(r'Message-ID:\s*([^\s]+)', headers, re.IGNORECASE)
    if match:
        msg_id = match.group(1).strip()
        if not msg_id.startswith('<'):
            msg_id = f"<{msg_id}>"
        return msg_id
    return None


def extract_references(headers: str | None) -> list[str]:
    """Extract References header (previous message IDs in thread)."""
    if not headers:
        return []
    match = re.search(r'References:\s*([^\r\n]+)', headers, re.IGNORECASE)
    if match:
        refs = match.group(1).strip()
        # Extract all message IDs between <>
        return re.findall(r'<([^>]+)>', refs)
    return []


@router.post("/inbound")
async def sendgrid_inbound(
    background_tasks: BackgroundTasks,
    from_email: str = Form(..., alias="from"),
    to: str = Form(...),
    subject: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    html: Optional[str] = Form(None),
    headers: Optional[str] = Form(None),
    attachments: Optional[int] = Form(None),
    dkim: Optional[str] = Form(None),
    SPF: Optional[str] = Form(None),
    envelope: Optional[str] = Form(None),
    charsets: Optional[str] = Form(None),
    spam_score: Optional[str] = Form(None),
    spam_report: Optional[str] = Form(None),
):
    """
    Receive inbound emails from SendGrid Inbound Parse webhook.
    SendGrid sends data as multipart/form-data, not JSON.
    Extracts Message-ID for proper email threading on replies.
    """
    try:
        # Parse envelope JSON to extract sender/recipient info
        envelope_data = json.loads(envelope) if envelope else {}
        from_addr = envelope_data.get("from", from_email)
        
        # Extract Message-ID from headers for reply threading
        message_id = extract_message_id(headers)
        references = extract_references(headers)
        
        
        # Build email content for the agent
        email_body = html or text or ""
        email_str = f"""Email Conversation ---
        Title: {subject}
        From: {from_email}
        To: {to}
        Body: {email_body}
        Message-ID: {message_id or 'N/A'}
        """
        
        # Look up customer by email
        customer = await CustomerDA().get_customer_by_email_address(from_addr)
        
        print(f"request: {email_str}")
        print(f"message_id: {message_id}")
        print(f"from_email: {from_addr}")
        print(f"to: {to}")
        print(f"subject: {subject}")
        print(f"references: {references}")

        agent_request: SendGridInboundRequest | None = None
        if "rxnorm" in to:
            agent_request = SendGridInboundRequest(
                agent_name="rxnorm_mapping_agent_email",
                request=email_str,
                message_id=message_id,
                from_email=from_addr,
                to=to,
                subject=subject,
                references=", ".join(references),
            )

        elif "support" in to:
            agent_request = SendGridInboundRequest(
                agent_name="customer_support_agent_email",
                request=email_str,
                message_id=message_id,
                from_email=from_addr,
                to=to,
                subject=subject,
                references=", ".join(references),
            )

        if agent_request is not None:
            # Send message to RabbitMQ
            RabbitMQService.asend_message(agent_request)

        return Response(status_code=200)
        
    except Exception as e:
        print(f"Error processing inbound email: {e}")
        return Response(status_code=200)