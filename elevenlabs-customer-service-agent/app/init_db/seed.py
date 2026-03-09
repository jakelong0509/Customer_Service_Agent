"""
Seed the database with synthetic data. Run after tables exist (see docs/database.md).

Usage (from project root):
    python -m app.init_db.seed
Or run the file directly (from any directory):
    python app/init_db/seed.py

Uses its own connection pool so it can run without starting the FastAPI app.
"""
import asyncio
import os
import sys
import uuid

# Ensure project root is on path so "app" can be imported
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import asyncpg

from app.config import get_settings


# Fixed UUIDs so we can link customers → orders, tickets, refunds, callbacks
C1 = uuid.UUID("11111111-0001-4000-8000-000000000001")
C2 = uuid.UUID("11111111-0002-4000-8000-000000000002")
C3 = uuid.UUID("11111111-0003-4000-8000-000000000003")
C4 = uuid.UUID("11111111-0004-4000-8000-000000000004")
C5 = uuid.UUID("11111111-0005-4000-8000-000000000005")


O1 = uuid.UUID("22222222-0001-4000-8000-000000000001")
O2 = uuid.UUID("22222222-0002-4000-8000-000000000002")
O3 = uuid.UUID("22222222-0003-4000-8000-000000000003")
O4 = uuid.UUID("22222222-0004-4000-8000-000000000004")
O5 = uuid.UUID("22222222-0005-4000-8000-000000000005")
O6 = uuid.UUID("22222222-0006-4000-8000-000000000006")


async def run_seed(conn: asyncpg.Connection) -> None:
    """Insert synthetic data. Caller must provide an open connection (e.g. from a pool)."""
    # Customers
    await conn.execute(
        """
        INSERT INTO customers (id, phone, email, name, plan, status)
        VALUES ($1, $2, $3, $4, $5, $6), ($7, $8, $9, $10, $11, $12),
               ($13, $14, $15, $16, $17, $18), ($19, $20, $21, $22, $23, $24),
               ($25, $26, $27, $28, $29, $30)
        ON CONFLICT (id) DO NOTHING
        """,
        C1, "+15551234001", "jane.doe@example.com", "Jane Doe", "premium", "active",
        C2, "+15551234002", "john.smith@example.com", "John Smith", "standard", "active",
        C3, "+15551234003", "alice.jones@example.com", "Alice Jones", "standard", "active",
        C4, "+15551234004", "bob.wilson@example.com", "Bob Wilson", "premium", "suspended",
        C5, "+15551234005", "carol.brown@example.com", "Carol Brown", "standard", "active",
    )

    # Orders
    await conn.execute(
        """
        INSERT INTO orders (id, customer_id, order_number, amount_cents, status)
        VALUES ($1, $2, 'ORD-1001', 4999, 'completed'), ($3, $2, 'ORD-1002', 1299, 'completed'),
               ($4, $5, 'ORD-1003', 8999, 'completed'), ($6, $5, 'ORD-1004', 2500, 'cancelled'),
               ($7, $8, 'ORD-1005', 5999, 'completed'), ($9, $10, 'ORD-1006', 1999, 'completed')
        ON CONFLICT (order_number) DO NOTHING
        """,
        O1, C1, 
        O2, 
        O3, C2, 
        O4, 
        O5, C3,
        O6, C4,
    )

    # Tickets (new rows each run; truncate tickets/refund_requests/callback_requests to re-seed cleanly)
    await conn.execute(
        """
        INSERT INTO tickets (id, customer_id, subject, description, status)
        VALUES (gen_random_uuid(), $1, 'Billing question', 'Charged twice last month', 'closed'),
               (gen_random_uuid(), $1, 'Feature request', 'Add dark mode to app', 'open'),
               (gen_random_uuid(), $2, 'Password reset', 'Cannot access account', 'in_progress'),
               (gen_random_uuid(), $3, 'Account suspension', 'Why was my account suspended?', 'open')
        """,
        C1, C2, C4,
    )

    # Refund requests
    await conn.execute(
        """
        INSERT INTO refund_requests (id, order_id, reason, status)
        VALUES (gen_random_uuid(), $1, 'Duplicate charge', 'approved'),
               (gen_random_uuid(), $2, 'Wrong size ordered', 'pending')
        """,
        O1, O3,
    )

    # Callback requests
    await conn.execute(
        """
        INSERT INTO callback_requests (id, customer_id, phone, requested_for, status)
        VALUES (gen_random_uuid(), $1, $2, 'next available', 'completed'),
               (gen_random_uuid(), $3, $4, 'tomorrow 2pm', 'pending'),
               (gen_random_uuid(), $5, $6, 'next available', 'pending')
        """,
        C1, "+15551234001", C2, "+15551234002", C3, "+15551234003",
    )

    # Appointments (scheduled_at as timestamptz; use now() + interval for demo)
    await conn.execute(
        """
        INSERT INTO appointments (id, customer_id, scheduled_at, subject, status, notes)
        VALUES (gen_random_uuid(), $1, now() + interval '2 days', 'Product demo', 'scheduled', '30 min call'),
               (gen_random_uuid(), $2, now() + interval '5 days', 'Support follow-up', 'scheduled', NULL),
               (gen_random_uuid(), $1, now() - interval '1 day', 'Billing review', 'completed', 'Resolved.'),
               (gen_random_uuid(), $3, now() + interval '1 week', 'Onboarding call', 'scheduled', 'New premium user'),
               (gen_random_uuid(), $4, now() - interval '3 days', 'Account review', 'cancelled', 'Customer rescheduled')
        """,
        C1, C2, C3, C4,
    )


async def main() -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=1,
        max_size=2,
        command_timeout=30,
    )
    try:
        async with pool.acquire() as conn:
            await run_seed(conn)
        print("Seed completed: customers, orders, tickets, refund_requests, callback_requests, appointments.")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
