---
name: appointment_booking_skill
description: >-
  Voice/agent workflow for clinic-style appointment scheduling: shared calendars per
  resource, 30-minute slots, availability search, alternatives, multi-resource booking,
  and confirm-before-write. Use when implementing or reviewing booking tools, prompts,
  or database logic for this project.
---

# Appointment booking skill

Guidance for the **agent** when handling **appointment scheduling** in this codebase.

---

## Available Tools

The following tools are exposed to the agent via `TOOLS` in `tools.py`:

### `create_appointment_resource_booking`
Creates an appointment with associated resource bookings (doctor + room) in a single transaction.

**Parameters:**
- `provider_ids`: list[str] - IDs of providers to book (e.g., [doctor_id, room_id])
- `slot_template_ids`: list[int] - IDs of slot templates for the appointment
- `scheduled_at`: datetime - The scheduled date and time
- `subject`: str - Purpose of the appointment
- `notes`: Optional[str] - Additional notes

**Behavior:**
1. Inserts into `appointments` table first
2. Then inserts into `appointment_resource_bookings` for each provider/slot combination
3. Returns JSON array of all created resource bookings
4. Uses `status = 2` (scheduled) for both tables

### `select_appointment_resource_bookings`
Query existing bookings for a specific date to check availability.

**Parameters:**
- `booking_date`: date - The date to query (e.g., "2026-03-26")

**Returns:** JSON array of all bookings on that date with provider and slot info.

### `select_providers`
Get all available providers with their types.

**Returns:** JSON array of providers with columns: `id`, `kind` (Doctor/Nurse/Room/Equipment), `name`, `active`.

**Query:** Joins `providers` with `provider_names` to get human-readable types.

### `select_slot_templates`
Get all available 30-minute time slots.

**Returns:** JSON array of slot templates with `id` and `start_time`.

---

## Table Schemas

### `providers` — Bookable resources (doctors, rooms, equipment)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| kind | INTEGER | FK to `provider_names` (1=Doctor, 2=Nurse, 3=Room, 4=Equipment) |
| name | VARCHAR(255) | Display name (e.g., "Dr. Smith", "Room A") |
| active | BOOLEAN | Is this resource currently active? |

### `provider_names` — Lookup table for resource types
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key |
| name | VARCHAR(255) | 'Doctor', 'Nurse', 'Room', 'Equipment' |

### `slot_templates` — Available 30-minute time slots
| Column | Type | Notes |
|--------|------|-------|
| id | SMALLINT | Primary key |
| start_time | TIME | 09:00, 09:30, ..., 16:30 (lunch 13:00-14:00 omitted) |

### `appointments` — The appointment entity
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| customer_id | UUID | FK to customers |
| scheduled_at | TIMESTAMPTZ | Actual date + time of appointment |
| subject | VARCHAR(255) | Appointment purpose |
| status | INTEGER | FK to `general_statuses` |
| notes | TEXT | Optional notes |

### `appointment_resource_bookings` — Resource reservations per appointment
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| appointment_id | UUID | FK to appointments (cascade delete) |
| provider_id | UUID | FK to providers |
| booking_date | DATE | The appointment date |
| slot_template_id | SMALLINT | FK to slot_templates |
| status | INTEGER | FK to `general_statuses` |
| **UNIQUE** | (provider_id, booking_date, slot_template_id) | Prevents double-booking |

### `general_statuses` — Status lookup
| id | name |
|----|------|
| 1 | pending |
| 2 | scheduled |
| 3 | completed |
| 4 | cancelled |

---

## Domain model (mental map)

- **Providers** (`providers`): bookable **resources**—doctors, nurses, rooms, equipment. Each has its **own** calendar for conflicts; same clock time for two doctors is **two different** slots.  
  - **Customer-facing booking is with a doctor.** Do **not** offer appointments "with" a **room** or **equipment** as the primary clinician; those kinds exist so the system can reserve **supporting resources** alongside the visit (and enforce no double-booking on rooms/equipment). Nurses may be attached to workflows later; default assumption: the caller is scheduling **doctor time** unless the product explicitly defines nurse-led visits.  
  - **No doctor named:** infer who to search from the request. Example: **general checkup** (or other department-level visit type) → search **availability across all doctors** in that **department** (or all clinic doctors if you have not modeled departments yet) and **recommend** concrete options ("Dr. Chen at 10:00 or Dr. Patel at 2:30"). If the caller names a doctor, scope search to that doctor (plus required room/equipment).  
  - **Never** let the customer book a visit as if the **sole** bookable party were a non-doctor **kind** when the intent is a standard medical appointment—keep **doctor selection** (explicit or "first available in scope") in the loop.

- **Slot templates** (`slot_templates`): fixed **30-minute** start times (clinic-local wall clock). **Lunch 13:00–14:00** is **not** represented as a template row—treat that window as never bookable when generating or offering times.
- **Appointments** (`appointments`): one row per visit (`scheduled_at` as `TIMESTAMPTZ`, `status` → `general_statuses`).
- **Resource bookings** (`appointment_resource_bookings`): **ledger of what is taken**. Rows are created when a booking is **confirmed**, not pre-generated for every empty cell. **Unique** `(provider_id, booking_date, slot_template_id)` prevents **double booking** on the same resource.
- **Multi-resource visits**: one appointment may need **several** providers (e.g. clinician + exam room). **Every** required resource must be free for the same **date + slot**; on confirm, insert **one booking row per resource** in the **same transaction** as the appointment (or fail and roll back).
  - **Rule: doctor always requires a room.** When booking any appointment with a doctor, you **must also** reserve an available exam room for that same slot. A doctor cannot see patients without a room.

---

## Conversation flow (what the agent should do)

1. **Collect constraints**  
   Reason or visit type (drives **which doctors** to consider—e.g. general checkup → all doctors in scope), **preferred date** and **time or window**, **named doctor** vs **first available doctor** in the department/clinic, and **timezone / clinic location** so "3 pm" is unambiguous.

2. **Search availability**  
   Use `select_providers` to get available doctors and rooms. Use `select_slot_templates` to get valid time slots. Use `select_appointment_resource_bookings` with the target date to check which slots are already taken. Do **not** guess times—query the actual bookings.

3. **If the exact time is unavailable**  
   Offer a **small set of concrete alternatives** (e.g., two or three options: date + time + resource if relevant)—not vague "we're busy."

4. **Explicit confirmation**  
   Read back the **chosen** slot (and key details) and get a clear **yes** before committing.

5. **Book**  
   Call `create_appointment_resource_booking` with:
   - `provider_ids`: [doctor_id, room_id] (both required)
   - `slot_template_ids`: [slot_id] (or multiple if booking spans multiple slots)
   - `scheduled_at`: The full datetime
   - `subject` and optional `notes`
   
   The tool handles inserting both the appointment and resource bookings atomically. If the unique constraint fails (double-booking), it returns an error and you should offer alternatives.

6. **Close the loop**  
   Confirm details once more and any practical next steps (arrival, forms, cancellation policy) if the product includes them.

---

## Status values (`general_statuses`)

Statuses are **lookup IDs** in the database (`pending`, `scheduled`, `completed`, `cancelled`). In application code, align with **`enums.py`** when behavior **branches** on a status; **rare ops** additions to the table may require a migration and, when logic cares about the new value, an **enum update**.
