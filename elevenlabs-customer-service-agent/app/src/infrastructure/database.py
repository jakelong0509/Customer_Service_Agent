# DB connection — async Postgres client via asyncpg
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg

from src.core.config import get_settings

_pool: asyncpg.Pool | None = None


async def init_pool() -> asyncpg.Pool:
    """Create and store the connection pool. Call once at app startup."""
    global _pool
    settings = get_settings()
    print(settings)
    _pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=1,
        max_size=10,
        command_timeout=60,
    )
    return _pool


def get_pool() -> asyncpg.Pool:
    """Return the current pool. Raises if pool not initialized."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() at startup.")
    return _pool


async def close_pool() -> None:
    """Close the connection pool. Call on app shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Acquire a connection from the pool for the duration of the context."""
    pool = get_pool()
    async with pool.acquire() as conn:
        yield conn


async def execute(query: str, *args: object) -> str:
    """Run a command (INSERT/UPDATE/DELETE). Returns status."""
    async with get_connection() as conn:
        return await conn.execute(query, *args)


async def fetch(query: str, *args: object) -> list[asyncpg.Record]:
    """Run a SELECT and return all rows."""
    async with get_connection() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query: str, *args: object) -> asyncpg.Record | None:
    """Run a SELECT and return one row or None."""
    async with get_connection() as conn:
        return await conn.fetchrow(query, *args)


async def fetchval(query: str, *args: object, column: int = 0) -> object:
    """Run a query and return a single value."""
    async with get_connection() as conn:
        return await conn.fetchval(query, *args, column=column)
