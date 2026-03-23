# FastAPI app — tool API only; Twilio and ElevenLabs configured on their dashboards
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import router as api_router
from src.infrastructure.database import close_pool, init_pool
from src.infrastructure.redis import close_redis, init_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB and Redis. Shutdown: close both."""
    await init_pool()
    await init_redis()
    yield
    await close_pool()
    await close_redis()


app = FastAPI(
    title="Customer Service Agent — Tools API",
    description="HTTP API for tools. Twilio and ElevenLabs are configured on their dashboards to call this API.",
    lifespan=lifespan,
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {"service": "customer-service-agent", "docs": "/docs"}
