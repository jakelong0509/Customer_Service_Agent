from pydantic import BaseModel, Field

class AgentRunRequest(BaseModel):
    agent_name: str = Field(..., description="Name of the agent to run (e.g. support_agent, customer_agent, IT_support_agent)")
    request: str = Field(..., description="Request to the agent")

class ElevenLabsAgentRunRequest(AgentRunRequest):
    """Request body for POST /api/agent/run. Dashboards (e.g. ElevenLabs webhook) send agent_name + parameters."""
    call_sid: str = Field(..., description="Caller SID")
    caller_phone_number: str = Field(..., description="Caller phone number")
    email_metadata: dict = Field(..., description="Email metadata")

class SendGridInboundRequest(BaseModel):
    """Request model for SendGrid Inbound Parse webhook.
    SendGrid sends data as multipart/form-data with these field names.
    """
    from_email: str = Field(alias="from", description="Sender email address (From: header)")
    to: str = Field(..., description="Recipient email address (To: header)")
    subject: str | None = Field(default=None, description="Email subject")
    text: str | None = Field(default=None, description="Plain text body")
    html: str | None = Field(default=None, description="HTML body content")
    headers: str | None = Field(default=None, description="Raw email headers")
    attachments: int | None = Field(default=None, description="Number of attachments")
    dkim: str | None = Field(default=None, description="DKIM verification result")
    SPF: str | None = Field(default=None, description="SPF verification result")
    envelope: str | None = Field(default=None, description="JSON envelope with to/from")
    charsets: str | None = Field(default=None, description="JSON charset information")
    spam_score: str | None = Field(default=None, description="Spam score")
    spam_report: str | None = Field(default=None, description="Spam report details")


class AgentRunResponse(BaseModel):
    result: str
    is_error: bool = False
    