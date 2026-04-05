import uuid
import json
from typing import Optional, List, Callable, Literal, Annotated
from langchain.tools import InjectedState, tool
from langgraph.runtime import get_runtime
from psycopg import Date
from pydantic import BaseModel, Field
from datetime import date, datetime, timezone
from src.core.customer import CustomerModel
from src.infrastructure.database import execute, fetch


TABLES = [
  "appointmnet_resource_bookings",
  "appointments",
  "providers",
  "provider_names",
  "slot_templates"
]

class SelectObject(BaseModel):
  table: Literal[*TABLES] = Field(..., description="The table to select data from")
  where: Optional[str] = Field(default=None, description="The where clause to select data from - e.g. booking_date = '2026-03-26'")


@tool
async def create_appointment_resource_booking(
  provider_ids: list[str]
  , slot_template_ids: list[int]
  , scheduled_at: datetime
  , subject: str
  , state: Annotated[BaseModel, InjectedState]
  , notes: Optional[str] = None
  ) -> list[str]:
  """Create an appointment resource booking for a provider and a slot template
  Args:
    provider_ids: list[str] - The ids of the providers to create a resource booking for
    slot_template_ids: list[int] - The ids of the slot templates to create a resource booking for
    scheduled_at: datetime - The scheduled date and time of the appointment
    subject: str - The subject of the appointment - if subject not clearly defined, make one based on the caller's request, this information is not important
    notes: str - The notes of the appointment - only when the caller requests or the agent decides to add notes - this information is not important
  Returns:
    str: Success message
  """
  customer = state.customer
  results = []
  try:
    rows = await fetch(
        "INSERT INTO appointments (customer_id, scheduled_at, subject, status, notes, created_at) VALUES ($1, $2, $3, $4, $5, $6) RETURNING *",
        customer.id,
        scheduled_at,
        subject,
        2,
        notes,
        datetime.now(timezone.utc),
    )
    appointment_inserted = dict(rows[0])  # Convert asyncpg.Record to dict
    if appointment_inserted:
      for slot_template_id in slot_template_ids:
        for provider_id in provider_ids:
          rows = await fetch(
            "INSERT INTO appointment_resource_bookings (appointment_id, provider_id, booking_date, slot_template_id, status) VALUES ($1, $2, $3, $4, $5) RETURNING *",
            appointment_inserted['id'],
            provider_id,
            scheduled_at.date(),
            slot_template_id,
            2,
          )
          resource_booking_inserted = dict(rows[0])  # Convert asyncpg.Record to dict
          if resource_booking_inserted:
            results.append(resource_booking_inserted)
    return json.dumps(results, default=str)  # Return as JSON string
  except Exception as e:
    return f"Error creating appointment resource booking: {e}"

# @tool
# async def select_action(
#   select: SelectObject
#   ) -> str:
#   """Use this tool when needed to select data from the database
  
#   Args:
#     select: SelectObject - The object containing the tables and where clause to select data from
#   """
#   try:
#     rows = await fetch(f"SELECT * FROM {select.table} {f'WHERE {select.where}' if select.where else ''}")
#     # Convert asyncpg.Record objects to dicts
#     rows_as_dicts = [dict(row) for row in rows]
#     # Return as JSON string for the LLM
#     return json.dumps(rows_as_dicts, default=str)  # default=str handles datetime/UUID
#   except Exception as e:
#     return f"Error selecting action: {e}"

@tool
async def select_appointment_resource_bookings(booking_date: date) -> str:
  """Select appointment resource bookings for a given booking date
  Args:
    booking_date: date - The date of the booking (e.g. "2026-03-26")
  Returns:
    str: JSON string with booking_date, start_time, Status, Provider Kind, and Provider
  """
  try:
    rows = await fetch(
      "SELECT * FROM get_appointment_details() WHERE booking_date = $1",
      booking_date
    )
    rows_as_dicts = [dict(row) for row in rows]
    return json.dumps(rows_as_dicts, default=str)  # Return as JSON string for the LLM
  except Exception as e:
    return f"Error selecting appointment resource bookings: {e}"

@tool
async def select_providers() -> str:
  """Select providers
  Args:
    None
  Returns:
    str: Success message
  """
  try:
    rows = await fetch("select a.id, b.name as \"kind\", a.name, a.active from providers a inner join provider_names b on a.kind = b.id")
    rows_as_dicts = [dict(row) for row in rows]
    return json.dumps(rows_as_dicts, default=str)  # Return as JSON string for the LLM
  except Exception as e:
    return f"Error selecting providers: {e}"

@tool
async def select_slot_templates() -> str:
  """Select slot templates
  Args:
    None
  Returns:
    str: Success message
  """
  try:
    rows = await fetch("SELECT * FROM slot_templates")
    rows_as_dicts = [dict(row) for row in rows]
    return json.dumps(rows_as_dicts, default=str)  # Return as JSON string for the LLM
  except Exception as e:
    return f"Error selecting slot templates: {e}"


TOOLS = [create_appointment_resource_booking, select_appointment_resource_bookings, select_providers, select_slot_templates]
def get_tools() -> List[Callable]:
  return TOOLS