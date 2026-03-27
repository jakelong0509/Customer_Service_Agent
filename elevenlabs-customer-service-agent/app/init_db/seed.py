"""
Load synthetic data from seed.sql. Run after tables exist (see docs/database.md).

Usage (from project root, with PYTHONPATH including `app`):
    python -m app.init_db.seed
Or:
    psql "$DATABASE_URL" -f app/init_db/seed.sql

Uses its own connection pool so it can run without starting the FastAPI app.
"""
import asyncio
import os
import sys
from pathlib import Path

# Ensure project root is on path so "app" / "src" can be imported
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import asyncpg

from src.core.config import get_settings

_SPLIT = "---- SPLIT ----"


def _load_seed_statements() -> list[str]:
    path = Path(__file__).with_name("seed.sql")
    text = path.read_text(encoding="utf-8")
    parts: list[str] = []
    for block in text.split(_SPLIT):
        stmt = block.strip()
        if not stmt:
            continue
        lines = [ln for ln in stmt.splitlines() if not ln.strip().startswith("--")]
        stmt = "\n".join(lines).strip()
        if stmt:
            parts.append(stmt)
    return parts


async def run_seed(conn: asyncpg.Connection) -> None:
    """Execute seed.sql statements in order."""
    for stmt in _load_seed_statements():
        await conn.execute(stmt)


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
        print(
            "Seed completed from seed.sql: customers, providers, callback_requests, "
            "appointments, appointment_resource_bookings (slot_templates from create_tables.sql)."
        )
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
