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

## Domain model (mental map)

- **Providers** (`providers`): bookable **resources**—doctors, nurses, rooms, equipment. Each has its **own** calendar for conflicts; same clock time for two doctors is **two different** slots.  
  - **Customer-facing booking is with a doctor.** Do **not** offer appointments “with” a **room** or **equipment** as the primary clinician; those kinds exist so the system can reserve **supporting resources** alongside the visit (and enforce no double-booking on rooms/equipment). Nurses may be attached to workflows later; default assumption: the caller is scheduling **doctor time** unless the product explicitly defines nurse-led visits.  
  - **No doctor named:** infer who to search from the request. Example: **general checkup** (or other department-level visit type) → search **availability across all doctors** in that **department** (or all clinic doctors if you have not modeled departments yet) and **recommend** concrete options (“Dr. Chen at 10:00 or Dr. Patel at 2:30”). If the caller names a doctor, scope search to that doctor (plus required room/equipment).  
  - **Never** let the customer book a visit as if the **sole** bookable party were a non-doctor **kind** when the intent is a standard medical appointment—keep **doctor selection** (explicit or “first available in scope”) in the loop.

- **Slot templates** (`slot_templates`): fixed **30-minute** start times (clinic-local wall clock). **Lunch 13:00–14:00** is **not** represented as a template row—treat that window as never bookable when generating or offering times.
- **Appointments** (`appointments`): one row per visit (`scheduled_at` as `TIMESTAMPTZ`, `status` → `general_statuses`).
- **Resource bookings** (`appointment_resource_bookings`): **ledger of what is taken**. Rows are created when a booking is **confirmed**, not pre-generated for every empty cell. **Unique** `(provider_id, booking_date, slot_template_id)` prevents **double booking** on the same resource.
- **Multi-resource visits**: one appointment may need **several** providers (e.g. clinician + exam room). **Every** required resource must be free for the same **date + slot**; on confirm, insert **one booking row per resource** in the **same transaction** as the appointment (or fail and roll back).

---

## Conversation flow (what the agent should do)

1. **Collect constraints**  
   Reason or visit type (drives **which doctors** to consider—e.g. general checkup → all doctors in scope), **preferred date** and **time or window**, **named doctor** vs **first available doctor** in the department/clinic, and **timezone / clinic location** so “3 pm” is unambiguous.

2. **Search availability**  
   Do **not** guess times from the model. Use tools/data to find slots over the **relevant doctor set** (one doctor if named; **all doctors in department/clinic** if undifferentiated checkup). Enumerate valid **slot templates** for the day (respect lunch, hours, days off, and any future **unavailability** rules), then for each candidate ensure **no conflicting booking** exists for **each** required resource (doctor plus any room/equipment the visit needs).

3. **If the exact time is unavailable**  
   Offer a **small set of concrete alternatives** (e.g. two or three options: date + time + resource if relevant)—not vague “we’re busy.”

4. **Explicit confirmation**  
   Read back the **chosen** slot (and key details) and get a clear **yes** before committing.

5. **Book**  
   Persist **`appointments`** and **`appointment_resource_bookings`** together; rely on **DB uniqueness** so concurrent requests cannot double-book. If insert fails, explain briefly and return to alternatives.

6. **Close the loop**  
   Confirm details once more and any practical next steps (arrival, forms, cancellation policy) if the product includes them.

---

## Status values (`general_statuses`)

Statuses are **lookup IDs** in the database (`pending`, `scheduled`, `completed`, `cancelled`). In application code, align with **`enums.py`** when behavior **branches** on a status; **rare ops** additions to the table may require a migration and, when logic cares about the new value, an **enum update**.

