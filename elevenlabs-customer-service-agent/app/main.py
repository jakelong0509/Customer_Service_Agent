# FastAPI app — tool API only; Twilio and ElevenLabs configured on their dashboards
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from controllers.routes import router as api_router
from controllers.elevenlabs_controller import router as elevenlabs_router
from src.infrastructure.database import close_pool, init_pool
from src.infrastructure.redis import close_redis, init_redis
from src.core.agent_run_request_model import AgentRunRequest
from src.services.agent_registry import create_agent
from src.agents.shared_tools.skill_tools import activate_skill, deactivate_skill
from src.agents.shared_tools.memory_tools import retrieve_conversation_history, store_conversation_history, store_session_outcome, find_similar_sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB and Redis. Shutdown: close both."""
    await init_pool()
    await init_redis()
    create_agent()
    yield
    await close_pool()
    await close_redis()


app = FastAPI(
    title="Customer Service Agent — Tools API",
    description="HTTP API for tools. Twilio and ElevenLabs are configured on their dashboards to call this API.",
    lifespan=lifespan,
)

app.include_router(api_router)
app.include_router(elevenlabs_router)


@app.get("/")
async def root():
    return {"service": "customer-service-agent", "docs": "/docs"}

@app.post("/webhooks/sendgrid-inbound")
async def sendgrid_inbound(request: Request):
    form_data = await request.form()

    # Key fields SendGrid sends:
    email_data = {
        "from": form_data.get("from"),
        "to": form_data.get("to"),
        "subject": form_data.get("subject"),
        "text": form_data.get("text"),        # Plain text body
        "html": form_data.get("html"),        # HTML body
        "headers": form_data.get("headers"),  # Raw email headers
        "attachments": form_data.get("attachments"),
        "message_id": form_data.get("message_id"),  # For threading/replies
    }
    
    email_str = f"""
    Title: {email_data.get("subject")}
    From: {email_data.get("from")}
    To: {email_data.get("to")}
    Body: {email_data.get("text")}
    """
    
    request = AgentRunRequest(
        agent_name="customer_support_agent",
        request=email_str
    )

    # First we will need to send this email content to the security agent, this agent will check if the email is spam or not. And if the email contains harmful content or not. Also check if the request is valid or not.
    # If not harmful, the agent will send the request to appropriate agent to handle the email.
    # Email processing, calling the agent to handle the email

    return {"status": "received"}  # Must return 2xx status