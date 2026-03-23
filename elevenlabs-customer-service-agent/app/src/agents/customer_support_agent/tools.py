from datetime import datetime, timezone
import uuid
from typing import Optional
from langchain_core.tools import tool
from langgraph.runtime import get_runtime

from src.core.customer import CustomerModel
from src.infrastructure.database import execute


@tool
async def create_appointment(scheduled_at: datetime, subject: str, notes: Optional[str] = None) -> str:
  """Create an appointment for a customer
  Args:
    scheduled_at: datetime - The scheduled date and time of the appointment
    subject: str - The subject of the appointment - if subject not clearly defined, make one based on the caller's request, this information is not important
    notes: str - The notes of the appointment - only when the caller requests or the agent decides to add notes - this information is not important
  Returns:
    str: Success message
  """
  runtime = get_runtime(CustomerModel)
  customer = runtime.context
  appointment_id = str(uuid.uuid4())
  try:
    # execute() is async — must await. It returns asyncpg status text (e.g. "INSERT 0 1"), not a model.
    await execute(
        "INSERT INTO appointments (id, customer_id, scheduled_at, subject, status, notes, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id",
        appointment_id,
        customer.id,
        scheduled_at,
        subject,
        "scheduled",
        notes,
        datetime.now(timezone.utc),
    )
    return (
        f"Appointment created successfully for customer {customer.id}, "
        f"id={appointment_id}, scheduled_at={scheduled_at}, subject={subject!r}"
    )
  except Exception as e:
    return f"Error creating appointment: {e}"
