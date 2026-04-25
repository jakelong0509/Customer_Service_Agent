# FastAPI app — tool API only; Twilio and ElevenLabs configured on their dashboards
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from controllers.routes import router as api_router
from controllers.elevenlabs_controller import router as elevenlabs_router
from controllers.sendgrid import router as sendgrid_router
from src.infrastructure.database import close_pool, init_pool
from src.infrastructure.redis import close_redis, init_redis
from src.agents.shared_tools import auto_register_tools
from src.services.agent_registry import create_agent
from src.infrastructure.milvus import close_milvus, init_milvus
from src.utils.logger import setup_logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB and Redis. Shutdown: close both."""
    setup_logging()
    init_milvus()
    await init_pool()
    await init_redis()
    create_agent()
    yield
    await close_pool()
    await close_redis()
    close_milvus()


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