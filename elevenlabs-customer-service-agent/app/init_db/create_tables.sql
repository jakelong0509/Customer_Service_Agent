-- Create tables for Customer Service Agent (see docs/database.md)
-- Run against your Postgres DB, e.g. psql $DATABASE_URL -f app/init_db/create_tables.sql

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
