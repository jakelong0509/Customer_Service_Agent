from pydantic import BaseModel, Field

class AgentRunRequest(BaseModel):
    agent_name: str = Field(..., description="Name of the agent to run (e.g. support_agent, customer_agent, IT_support_agent)")
    request: str = Field(..., description="Request to the agent")

class ElevenLabsAgentRunRequest(AgentRunRequest):
    """Request body for POST /api/agent/run. Dashboards (e.g. ElevenLabs webhook) send agent_name + parameters."""
    call_sid: str = Field(..., description="Caller SID")
    caller_phone_number: str = Field(..., description="Caller phone number")
    email_metadata: dict = Field(..., description="Email metadata")

class SendGridInboundRequest(AgentRunRequest):
    """Request model for SendGrid Inbound Parse webhook.
    SendGrid sends data as multipart/form-data with these field names.
    """
    message_id: str = Field(..., description="Message-ID of the email")
    from_email: str = Field(..., description="Sender email address (From: header)")
    to: str = Field(..., description="Recipient email address (To: header)")
    subject: str | None = Field(default=None, description="Email subject")
    references: str | None = Field(default=None, description="Comma-separated previous Message-IDs in the thread")


class AgentRunResponse(BaseModel):
    result: str
    is_error: bool = False
    