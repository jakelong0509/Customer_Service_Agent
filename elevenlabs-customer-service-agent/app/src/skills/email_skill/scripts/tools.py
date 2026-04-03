import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Header
from python_http_client.exceptions import HTTPError
from langchain.tools import tool
import dotenv
from typing import List, Callable, Optional
dotenv.load_dotenv()


async def _send_email_impl(
    to_email: str,
    subject: str,
    body: str,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None
) -> str:
    """
    Internal helper function to send email via SendGrid.
    This is NOT a tool - it's called by the tools to avoid tool-calling-tool issues.
    """
    try:
        message = Mail(
            from_email=os.getenv("SENDGRID_FROM_EMAIL"),
            to_emails=to_email,
            subject=subject,
            html_content=body
        )
        
        # Add threading headers for proper email conversation
        if in_reply_to:
            message.headers = message.headers or []
            message.headers.append(Header("In-Reply-To", in_reply_to))
        
        if references:
            message.headers = message.headers or []
            message.headers.append(Header("References", references))
        
        sendgrid_client = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        response = sendgrid_client.send(message)
        
        if response.status_code == 202:
            return f"Email sent successfully to {to_email}"
        else:
            return f"Error sending email: HTTP {response.status_code} - {response.body}"
            
    except HTTPError as e:
        return f"SendGrid API error: {e.to_dict}"
    except Exception as e:
        return f"Error sending email: {e}"


@tool
async def send_email(
    recipient_email_address: str,
    subject: str,
    body: str
) -> str:
    """
    Send a new email to a customer.
    
    Use this for:
    - Proactive notifications (order updates, alerts)
    - Initial outreach to customers
    - Any email that is NOT a reply to a received email
    
    For REPLIES to inbound emails, use the reply_to_email tool instead.
    
    Args:
        recipient_email_address: str - The email address to send to
        subject: str - The subject line (e.g., "Your Order Update")
        body: str - The HTML body of the email
    
    Returns:
        str: Success message or error details
    """
    return await _send_email_impl(
        to_email=recipient_email_address,
        subject=subject,
        body=body
    )


@tool
async def reply_to_email(
    original_message_id: str,
    original_sender: str,
    original_subject: str,
    reply_body: str,
    references: Optional[str] = None
) -> str:
    """
    Reply to a received email with proper threading headers.
    
    This ensures the reply appears in the same Gmail/Outlook thread as the original email.
    
    Args:
        original_message_id: str - The Message-ID from the email being replied to (format: <id@domain.com>)
        original_sender: str - The email address of the person who sent the original email
        original_subject: str - The subject of the original email (will be prefixed with "Re: ")
        reply_body: str - The HTML content of your reply
        references: Optional[str] - Comma-separated list of previous Message-IDs in the thread
    
    Returns:
        str: Success message or error details
    
    Example:
        reply_to_email(
            original_message_id="<abc123@sender-domain.com>",
            original_sender="customer@example.com",
            original_subject="Help with my order",
            reply_body="<p>Thank you for contacting us...</p>"
        )
    """
    try:
        # Build subject with Re: prefix (if not already present)
        subject = original_subject
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        
        # Build references chain
        refs = references or ""
        if original_message_id:
            if refs:
                refs = f"{refs}, {original_message_id}"
            else:
                refs = original_message_id
        
        # Call the shared implementation
        return await _send_email_impl(
            to_email=original_sender,
            subject=subject,
            body=reply_body,
            in_reply_to=original_message_id,
            references=refs
        )
        
    except Exception as e:
        return f"Error creating reply: {e}"


TOOLS = [send_email, reply_to_email]
def get_tools() -> List[Callable]:
    return TOOLS