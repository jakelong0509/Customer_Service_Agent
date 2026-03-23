from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import uuid
from zoneinfo import ZoneInfo

class AppointmentModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scheduled_at: datetime = Field(description="The scheduled date and time of the appointment")
    subject: str = Field(description="The subject of the appointment")
    status: str = Field(description="The status of the appointment")
    notes: str = Field(description="The notes of the appointment")
    created_at: datetime = Field(default_factory=lambda: datetime.now(ZoneInfo("UTC")))