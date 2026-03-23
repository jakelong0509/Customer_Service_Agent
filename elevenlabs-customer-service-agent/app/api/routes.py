# HTTP routes — health and tool API (Twilio/ElevenLabs call these from their dashboards)
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from src.services.dispatch_agent import invoke_agent
from src.core.agent_run_request_model import AgentRunRequest, AgentRunResponse

from src.core.conversation import CallContext
from src.core.customer import CustomerModel
from DAL.customerDA import CustomerDA

router = APIRouter(prefix="/api", tags=["api"])

@router.get("/health")
async def health():
    """Health check for load balancers and readiness probes."""
    return {"status": "ok"}


@router.post("/agent/run", response_model=AgentRunResponse)
async def agent_run(
    body: AgentRunRequest
):
    """
    Run a tool by name. Called by Twilio/ElevenLabs (or other systems) when they need to execute a tool.
    Pass tool_name and parameters in the body; optional context (call_sid, from, to) in body or headers.
    """

    customer = await CustomerDA().get_customer_by_phone_number(body.caller_phone_number)
    print(f"Phone number: {body.caller_phone_number}")
    print(f"Customer: {customer}")
    result = await invoke_agent(body, customer)
    is_error = result.startswith("Error:") if isinstance(result, str) else False
    return AgentRunResponse(result=result, is_error=is_error)

@router.get("/customer/{caller_phone_number}", response_model=CustomerModel)
async def get_customer_by_phone_number(caller_phone_number: str) -> CustomerModel:
    try:
        customer = await CustomerDA().get_customer_by_phone_number(caller_phone_number)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

# async def initialize_agent_for_call(body: AgentRunRequest, call_sid: str, caller_number: str) -> str:
#     context = CallContext(
#         call_sid = call_sid,
#         from_number = caller_number
#     )
#     try:
#         await initialize_call(call_sid, caller_number)