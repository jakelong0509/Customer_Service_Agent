# HTTP routes — health and tool API (Twilio/ElevenLabs call these from their dashboards)
from fastapi import APIRouter, HTTPException
from src.services.dispatch_agent import invoke_agent
from src.core.agent_run_request_model import ElevenLabsAgentRunRequest, AgentRunResponse

from src.core.customer import CustomerModel
from DAL.customerDA import CustomerDA

router = APIRouter(prefix="/api/elevenlabs", tags=["api"])

# Step 1: Elevenlabs calls this endpoint to get the customer information by phone number
@router.get("/customer/{caller_phone_number}", response_model=CustomerModel)
async def get_customer_by_phone_number(caller_phone_number: str) -> CustomerModel:
    try:
        customer = await CustomerDA().get_customer_by_phone_number(caller_phone_number)
        # If the customer is not found, which means the customer is unregistered, create a new customer
        if customer is None:
            customer = await CustomerDA().create_customer(CustomerModel(
                phone=caller_phone_number,
                email="",
                name="Unregistered Customer",
                plan="Free",
                status="active",
            ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

# Step 2: Elevenlabs calls this endpoint to run the agent 
@router.post("/agent/run", response_model=AgentRunResponse)
async def agent_run(
    body: ElevenLabsAgentRunRequest,
):
    """
    Run a tool by name. Called by Twilio/ElevenLabs (or other systems) when they need to execute a tool.
    Pass tool_name and parameters in the body; optional context (call_sid, from_number) in body or headers.
    """
    # Since in the step 1, we making sure the customer is created 
    customer = await CustomerDA().get_customer_by_phone_number(body.caller_phone_number)
    print(f"Phone number: {body.caller_phone_number}")
    print(f"Customer: {customer}")
    result = await invoke_agent(body.agent_name, body, customer, body.call_sid)
    is_error = result.startswith("Error:") if isinstance(result, str) else False
    return AgentRunResponse(result=result, is_error=is_error)

# Step 3: Elevenlabs calls this endpoint when ending the call, to remove thread_id and store the conversation history in the database.
@router.post("/agent/end", response_model=AgentRunResponse)
async def agent_end(
    body: ElevenLabsAgentRunRequest,
):
    """
    End a call. Called by Twilio/ElevenLabs (or other systems) when they need to end a call.
    Pass tool_name and parameters in the body; optional context (call_sid, from_number) in body or headers.
    """
    # Have to do this because we only have 1 agent run for all customer, we need to know which customer is ending the call.
    customer = await CustomerDA().get_customer_by_phone_number(body.caller_phone_number)
    result = await invoke_agent(body.agent_name, body, customer, body.call_sid)
    is_error = result.startswith("Error:") if isinstance(result, str) else False
    return AgentRunResponse(result=result, is_error=is_error)

# async def initialize_agent_for_call(body: AgentRunRequest, call_sid: str, caller_number: str) -> str:
#     context = CallContext(
#         call_sid = call_sid,
#         from_number = caller_number
#     )
#     try:
#         await initialize_call(call_sid, caller_number)