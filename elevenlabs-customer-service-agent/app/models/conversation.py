# Call/session context for tool invocations (optional, from API request)
from pydantic import BaseModel, Field


class CallContext(BaseModel):
    """Optional context for tool calls; can be passed via API body or headers."""

    call_sid: str = Field(default="", description="Call or session ID")
    from_number: str = Field(default="", description="Caller phone number")
    to_number: str = Field(default="", description="Called number")
