# FastAPI app — tool API only; Twilio and ElevenLabs configured on their dashboards
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from controllers.routes import router as api_router
from controllers.elevenlabs_controller import router as elevenlabs_router
from controllers.sendgrid import router as sendgrid_router
from src.infrastructure.database import close_pool, init_pool
from src.infrastructure.redis import close_redis, init_redis
from src.services.agent_registry import create_agent
from src.agents.shared_tools.skill_tools import activate_skill, deactivate_skill
from src.agents.shared_tools.memory_tools import retrieve_conversation_history, store_conversation_history, store_session_outcome, find_similar_sessions
from src.services.dispatch_agent import invoke_agent
from DAL.customerDA import CustomerDA
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
app.include_router(sendgrid_router)

@app.get("/")
async def root():
    return {"service": "customer-service-agent", "docs": "/docs"}