# Database structure

Simple schema for the tool API: customers, orders, tickets, refunds, callbacks, and appointments. Postgres, managed via asyncpg.

---

## Overview

```
customers          orders              tickets
    |                  |                    |
    +--< orders        +--< refund_requests
    +--< tickets
    +--< callback_requests
    +--< appointments
```

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
- Used by: `lookup_customer`, `get_account_info`, and as FK for tickets/orders/callbacks.

---

### `orders`

| Column       | Type         | Nullable | Description                |
|-------------|--------------|----------|----------------------------|
| id          | UUID         | no       | Primary key                |
| customer_id | UUID         | yes      | FK → customers.id          |
| order_number| VARCHAR(64)  | no       | External ref (e.g. ORD-123) |
| amount_cents| INT          | yes      |                            |
| status      | VARCHAR(32)  | no       | e.g. completed, cancelled  |
| created_at  | TIMESTAMPTZ  | no       | Default now()              |

- Unique index on `order_number`.
- Used by: `check_refund_eligibility`, `request_refund`.

---

### `tickets`

| Column       | Type         | Nullable | Description                |
|-------------|--------------|----------|----------------------------|
| id          | UUID         | no       | Primary key                |
| customer_id | UUID         | yes      | FK → customers.id          |
| subject     | VARCHAR(255) | no       |                            |
| description | TEXT         | yes      |                            |
| status      | VARCHAR(32)  | no       | e.g. open, in_progress, closed |
| created_at  | TIMESTAMPTZ  | no       | Default now()              |
| updated_at  | TIMESTAMPTZ  | no       | Default now()              |

- Used by: `create_ticket`.

---

### `refund_requests`

| Column       | Type         | Nullable | Description                |
|-------------|--------------|----------|----------------------------|
| id          | UUID         | no       | Primary key                |
| order_id    | UUID         | no       | FK → orders.id             |
| reason      | TEXT         | yes      |                            |
| status      | VARCHAR(32)  | no       | e.g. pending, approved, rejected |
| created_at  | TIMESTAMPTZ  | no       | Default now()              |

- Used by: `request_refund`.

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
| scheduled_at| TIMESTAMPTZ  | no       | When the appointment is    |
| subject     | VARCHAR(255) | no       | e.g. "Product demo", "Support follow-up" |
| status      | VARCHAR(32)  | no       | e.g. scheduled, completed, cancelled |
| notes       | TEXT         | yes      |                            |
| created_at  | TIMESTAMPTZ  | no       | Default now()              |

- Used for scheduled appointments (e.g. callbacks, demos, follow-ups).

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

CREATE TABLE orders (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id  UUID REFERENCES customers (id) ON DELETE SET NULL,
    order_number VARCHAR(64) NOT NULL,
    amount_cents INT,
    status       VARCHAR(32) NOT NULL DEFAULT 'completed',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idx_orders_order_number ON orders (order_number);

CREATE TABLE tickets (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers (id) ON DELETE SET NULL,
    subject     VARCHAR(255) NOT NULL,
    description TEXT,
    status      VARCHAR(32) NOT NULL DEFAULT 'open',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE refund_requests (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id   UUID NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    reason     TEXT,
    status     VARCHAR(32) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

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
```

---

## Notes

- All PKs are UUIDs; use `gen_random_uuid()` so the app doesn’t need to generate them if you run raw SQL.
- Timestamps are UTC (`TIMESTAMPTZ`).
- Optional FKs use `ON DELETE SET NULL` so deleting a customer doesn’t delete tickets/orders; refunds are tied to orders with `ON DELETE CASCADE`.
- Add indexes on `customer_id` and `order_id` and any columns you filter on often (e.g. `tickets.status`, `orders.created_at`) when you add more queries.
