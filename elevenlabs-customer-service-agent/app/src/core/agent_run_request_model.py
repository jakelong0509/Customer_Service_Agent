from pydantic import BaseModel, Field

class AgentRunRequest(BaseModel):
    """Request body for POST /api/agent/run. Dashboards (e.g. ElevenLabs webhook) send agent_name + parameters."""
    agent_name: str = Field(..., description="Name of the agent to run (e.g. support_agent, customer_agent, IT_support_agent)")
    request: str = Field(..., description="Request to the agent")
    call_sid: str = Field(..., description="The call SID")
    caller_phone_number: str = Field(..., description="The caller phone number")


class AgentRunResponse(BaseModel):
    result: str
    is_error: bool = False
