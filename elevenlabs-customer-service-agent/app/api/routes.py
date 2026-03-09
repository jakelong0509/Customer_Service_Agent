# HTTP routes — health and tool API (Twilio/ElevenLabs call these from their dashboards)
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.models.conversation import CallContext
from app.services.tool_dispatcher import dispatch as dispatch_tool

router = APIRouter(prefix="/api", tags=["api"])


class ToolRunRequest(BaseModel):
    """Request body for POST /api/tools/run. Dashboards (e.g. ElevenLabs webhook) send tool_name + parameters."""

    tool_name: str = Field(..., description="Name of the tool to run (e.g. lookup_customer, create_ticket)")
    parameters: dict = Field(default_factory=dict, description="Tool arguments")
    call_sid: str = Field(default="", description="Optional call/session ID for context")
    from_number: str = Field(default="", description="Optional caller number")
    to_number: str = Field(default="", description="Optional called number")


class ToolRunResponse(BaseModel):
    result: str
    is_error: bool = False


@router.get("/health")
async def health():
    """Health check for load balancers and readiness probes."""
    return {"status": "ok"}


@router.post("/tools/run", response_model=ToolRunResponse)
async def tools_run(
    body: ToolRunRequest,
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
        result = await dispatch_tool(body.tool_name, body.parameters, context)
        is_error = result.startswith("Error:") if isinstance(result, str) else False
        return ToolRunResponse(result=result, is_error=is_error)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
