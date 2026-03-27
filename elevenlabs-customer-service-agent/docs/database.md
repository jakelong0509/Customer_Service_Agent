# Database structure

Schema for the tool API: **customers**, **providers** (doctors, nurses, rooms, equipment), **slot_templates** (fixed 30-minute grid with lunch omitted), **appointments**, **appointment_resource_bookings** (per-resource reservations to prevent double booking), and **callback_requests**. Postgres, managed via asyncpg.

---

## Overview

```
customers
    |
    +--< callback_requests
    +--< appointments
              |
              +--< appointment_resource_bookings >-- providers
                                          \-- slot_templates
```

- **No pre-generated “available” rows.** `appointment_resource_bookings` rows are inserted when an appointment is **confirmed** (one row per reserved resource per 30-minute slot).
- **Multi-resource visits:** the same `appointment_id` appears on several booking rows (e.g. doctor + exam room). A **unique** constraint on `(provider_id, booking_date, slot_template_id)` stops the same resource from being booked twice for that slot.
- **Slot templates** use **clinic-local wall-clock** `TIME` values. `appointments.scheduled_at` is **`TIMESTAMPTZ`** (typically UTC in the app). The app must keep `booking_date` + `slot_template_id` consistent with `scheduled_at` (and your chosen clinic timezone). Demo seeds may assume UTC = local for simplicity.

---

## Tables

### `customers`

| Column       | Type         | Nullable | Description                |
|-------------|--------------|----------|----------------------------|
| id          | UUID         | no       | Primary key (default gen_random_uuid()) |
| phone       | VARCHAR(32)  | yes      | E.164 or normalized       |
| email       | VARCHAR(255) | yes      |                            |
| name        | VARCHAR(255) | yes      | Display name               |
| plan        | VARCHAR(64)  | yes      | e.g. standard, premium     |
| status      | VARCHAR(32)  | no       | e.g. active, suspended     |
| created_at  | TIMESTAMPTZ  | no       | Default now()              |
| updated_at  | TIMESTAMPTZ  | no       | Default now()              |

- Unique index on `phone` (where not null).
- Used by: `lookup_customer`, `get_account_info`, and as FK for callbacks and appointments.

---

### `providers`

| Column       | Type         | Nullable | Description                |
|-------------|--------------|----------|----------------------------|
| id          | UUID         | no       | Primary key                |
| kind        | VARCHAR(32)  | no       | `doctor`, `nurse`, `room`, `equipment` |
| name        | VARCHAR(255) | no       | Display name               |
| active      | BOOLEAN      | no       | Default true               |
| created_at  | TIMESTAMPTZ  | no       | Default now()              |

- Check constraint on `kind`.
- Index on `kind` where `active` (for filtering bookable resources).

---

### `slot_templates`

| Column       | Type         | Nullable | Description                |
|-------------|--------------|----------|----------------------------|
| id          | SMALLINT     | no       | Primary key (seeded 1–12)  |
| start_time  | TIME         | no       | Start of 30-minute bucket; unique |

- Seeded in **`app/init_db/create_tables.sql`**: morning **09:00–12:00** and afternoon **14:00–17:00** in 30-minute steps (**13:00–14:00 lunch** has no template row).
- Availability search generates candidates from these times (plus rules for days off, etc.) and checks for **missing** booking rows per required provider.

---

### `callback_requests`

| Column        | Type         | Nullable | Description                |
|---------------|--------------|----------|----------------------------|
| id            | UUID         | no       | Primary key                |
| customer_id   | UUID         | yes      | FK → customers.id          |
| phone         | VARCHAR(32)  | no       | Number to call back        |
| requested_for | VARCHAR(128) | yes      | e.g. "next available", "tomorrow 2pm" |
| status        | VARCHAR(32)  | no       | e.g. pending, completed    |
| created_at    | TIMESTAMPTZ  | no       | Default now()              |

- Used by: `schedule_callback`.

---

### `appointments`

| Column       | Type         | Nullable | Description                |
|-------------|--------------|----------|----------------------------|
| id          | UUID         | no       | Primary key                |
| customer_id | UUID         | yes      | FK → customers.id          |
| scheduled_at| TIMESTAMPTZ  | no       | Start of the visit         |
| subject     | VARCHAR(255) | no       | e.g. visit reason / label  |
| status      | VARCHAR(32)  | no       | e.g. scheduled, completed, cancelled |
| notes       | TEXT         | yes      |                            |
| created_at  | TIMESTAMPTZ  | no       | Default now()              |

- Indexes on `scheduled_at`, `customer_id`.
- Used with **`appointment_resource_bookings`** when reserving doctors, rooms, or equipment.

---

### `appointment_resource_bookings`

| Column           | Type         | Nullable | Description                |
|------------------|--------------|----------|----------------------------|
| id               | UUID         | no       | Primary key                |
| appointment_id   | UUID         | no       | FK → appointments.id (CASCADE) |
| provider_id      | UUID         | no       | FK → providers.id          |
| booking_date     | DATE         | no       | Calendar date for the slot |
| slot_template_id | SMALLINT     | no       | FK → slot_templates.id     |
| status           | VARCHAR(32)  | no       | `booked` (default) or `pending` (optional holds) |
| created_at       | TIMESTAMPTZ  | no       | Default now()              |

- **Unique** `(provider_id, booking_date, slot_template_id)` — prevents double booking per resource.
- Indexes for availability lookups and by `appointment_id`.

---

## SQL (create tables)

Script file: **`app/init_db/create_tables.sql`** — run with `psql $DATABASE_URL -f app/init_db/create_tables.sql` or paste the block below.

```sql
-- Create tables for Customer Service Agent
-- CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE customers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone       VARCHAR(32),
    email       VARCHAR(255),
    name        VARCHAR(255),
    plan        VARCHAR(64),
    status      VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idx_customers_phone ON customers (phone) WHERE phone IS NOT NULL;

CREATE TABLE providers (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind       VARCHAR(32) NOT NULL
        CHECK (kind IN ('doctor', 'nurse', 'room', 'equipment')),
    name       VARCHAR(255) NOT NULL,
    active     BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_providers_kind ON providers (kind) WHERE active = true;

CREATE TABLE slot_templates (
    id         SMALLINT PRIMARY KEY,
    start_time TIME NOT NULL UNIQUE
);

INSERT INTO slot_templates (id, start_time) VALUES
    (1, '09:00'), (2, '09:30'), (3, '10:00'), (4, '10:30'), (5, '11:00'), (6, '11:30'),
    (7, '14:00'), (8, '14:30'), (9, '15:00'), (10, '15:30'), (11, '16:00'), (12, '16:30')
ON CONFLICT (id) DO NOTHING;

CREATE TABLE callback_requests (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id   UUID REFERENCES customers (id) ON DELETE SET NULL,
    phone         VARCHAR(32) NOT NULL,
    requested_for VARCHAR(128),
    status        VARCHAR(32) NOT NULL DEFAULT 'pending',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE appointments (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id  UUID REFERENCES customers (id) ON DELETE SET NULL,
    scheduled_at TIMESTAMPTZ NOT NULL,
    subject      VARCHAR(255) NOT NULL,
    status       VARCHAR(32) NOT NULL DEFAULT 'scheduled',
    notes        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_appointments_scheduled_at ON appointments (scheduled_at);
CREATE INDEX idx_appointments_customer_id ON appointments (customer_id);

CREATE TABLE appointment_resource_bookings (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id   UUID NOT NULL REFERENCES appointments (id) ON DELETE CASCADE,
    provider_id      UUID NOT NULL REFERENCES providers (id) ON DELETE RESTRICT,
    booking_date     DATE NOT NULL,
    slot_template_id SMALLINT NOT NULL REFERENCES slot_templates (id) ON DELETE RESTRICT,
    status           VARCHAR(32) NOT NULL DEFAULT 'booked'
        CHECK (status IN ('booked', 'pending')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider_id, booking_date, slot_template_id)
);
CREATE INDEX idx_appointment_resource_bookings_lookup
    ON appointment_resource_bookings (provider_id, booking_date);
CREATE INDEX idx_appointment_resource_bookings_appointment
    ON appointment_resource_bookings (appointment_id);
```

---

## Notes

- All PKs are UUIDs except `slot_templates.id` (SMALLINT); use `gen_random_uuid()` where applicable.
- Timestamps are UTC (`TIMESTAMPTZ`).
- Optional FKs use `ON DELETE SET NULL` on `customers` so deleting a customer does not cascade to appointments unless you change that later.
- **Lunch, sick days, vacation:** model with application rules and/or a future `provider_unavailability` table; they are not stored as rows in `appointment_resource_bookings`.
- Add further indexes when you filter heavily on `appointments.status` or date ranges.
