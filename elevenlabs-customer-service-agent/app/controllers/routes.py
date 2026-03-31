# HTTP routes — health and tool API (Twilio/ElevenLabs call these from their dashboards)
from fastapi import APIRouter


router = APIRouter(prefix="/api", tags=["api"])

@router.get("/health")
async def health():
    """Health check for load balancers and readiness probes."""
    return {"status": "ok"}
