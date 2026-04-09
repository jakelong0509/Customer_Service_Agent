# HTTP routes — health and tool API for SendGrid Inbound Parse webhook
from fastapi import APIRouter, HTTPException, Form
from typing import Optional
import json
import re
from src.services.dispatch_agent import invoke_agent
from src.core.agent_run_request_model import ElevenLabsAgentRunRequest, AgentRunResponse

from src.core.customer import CustomerModel
from DAL.customerDA import CustomerDA

router = APIRouter(prefix="/api/sendgrid", tags=["api"])


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


@router.post("/inbound", response_model=AgentRunResponse)
async def sendgrid_inbound(
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
        
        # Create a unique conversation ID for this email thread
        # Use Message-ID if available for more accurate threading
        thread_id = message_id.strip('<>').replace('@', '_').replace('.', '_') if message_id else f"{from_addr.replace('@', '_')}_{subject or 'no_subject'}"
        conversation_id = f"email_{thread_id[:200]}"  # Limit length
        
        # Store email metadata in the request for the agent to save
        # The agent should store: message_id, from_addr, to, subject in conversation history
        email_metadata = {
            "message_id": message_id,
            "from": from_addr,
            "to": to,
            "subject": subject,
            "references": references,
        }
        
        # Build agent run request with email metadata
        # full_request = f"""{email_str}

        # EMAIL_METADATA: {json.dumps(email_metadata)}

        # Instructions: When replying to this email, activate the skill **email_skill** and call the tool **reply_to_email** and pass the following parameters: 
        # - original_message_id: {message_id}
        # - original_sender: {from_addr}
        # - original_subject: {subject}
        # - references: {references}
        # """
        
        
        agent_request = ElevenLabsAgentRunRequest(
            agent_name="customer_support_agent_email",
            request=email_str,
            call_sid=conversation_id[:255],
            caller_phone_number=from_addr,
            email_metadata=email_metadata
        )
        
        # Process through agent
        result = await invoke_agent(
            agent_request.agent_name,
            agent_request,
            customer,
            agent_request.call_sid
        )
        
        is_error = result.startswith("Error:") if isinstance(result, str) else False
        return AgentRunResponse(result=result, is_error=is_error)
        
    except Exception as e:
        print(f"Error processing inbound email: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing email: {str(e)}") from e