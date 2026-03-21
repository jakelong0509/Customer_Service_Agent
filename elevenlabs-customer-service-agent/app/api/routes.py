# HTTP routes — health and tool API (Twilio/ElevenLabs call these from their dashboards)
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from ..services.dispatch_agent import invoke_agent

from app.models.conversation import CallContext

router = APIRouter(prefix="/api", tags=["api"])


class AgentRunRequest(BaseModel):
    """Request body for POST /api/agent/run. Dashboards (e.g. ElevenLabs webhook) send agent_name + parameters."""
    agent_name: str = Field(..., description="Name of the agent to run (e.g. support_agent, customer_agent, IT_support_agent)")
    parameters: dict = Field(default_factory=dict, description="Agent arguments")
    request: str = Field(..., description="Request to the agent")


class AgentRunResponse(BaseModel):
    result: str
    is_error: bool = False


@router.get("/health")
async def health():
    """Health check for load balancers and readiness probes."""
    return {"status": "ok"}


@router.post("/agent/run", response_model=AgentRunResponse)
async def agent_run(
    body: AgentRunRequest,
    x_call_sid: str | None = Header(None, alias="X-Call-Sid"),
    x_from: str | None = Header(None, alias="X-From"),
    x_to: str | None = Header(None, alias="X-To"),
):
    """
    Run a tool by name. Called by Twilio/ElevenLabs (or other systems) when they need to execute a tool.
    Pass tool_name and parameters in the body; optional context (call_sid, from, to) in body or headers.
    """
    context = CallContext(
        call_sid=body.call_sid or x_call_sid or "",
        from_number=body.from_number or x_from or "",
        to_number=body.to_number or x_to or "",
    )
    try:
        result = await invoke_agent(body, context)
        is_error = result.startswith("Error:") if isinstance(result, str) else False
        return AgentRunResponse(result=result, is_error=is_error)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
