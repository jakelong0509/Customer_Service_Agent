# Tool registration — name -> async function for agent tool calls
import asyncio
import logging
from typing import Any, Callable, Awaitable

from app.models.conversation import CallContext

logger = logging.getLogger(__name__)

# name -> async (arguments: dict, context: CallContext) -> str | dict
ToolFunc = Callable[[dict[str, Any], CallContext], Awaitable[str | dict]]
REGISTRY: dict[str, ToolFunc] = {}


def register(name: str) -> Callable[[ToolFunc], ToolFunc]:
    """Decorator to register an async tool function. Function signature: (arguments, context) -> result (str or dict)."""

    def decorator(fn: ToolFunc) -> ToolFunc:
        REGISTRY[name] = fn
        return fn

    return decorator


def get(name: str) -> ToolFunc | None:
    return REGISTRY.get(name)


async def run(
    name: str,
    arguments: dict[str, Any],
    context: CallContext,
    *,
    timeout_seconds: float = 30.0,
    semaphore: asyncio.Semaphore | None = None,
) -> str | dict:
    """
    Run a registered tool by name. Returns result (str or dict to be serialized for the agent).
    Uses timeout to avoid blocking forever; optional semaphore to limit concurrency.
    """
    fn = get(name)
    if not fn:
        return f"Error: unknown tool '{name}'"

    async def _run() -> str | dict:
        if semaphore:
            async with semaphore:
                return await fn(arguments, context)
        return await fn(arguments, context)

    try:
        return await asyncio.wait_for(_run(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning("Tool %s timed out after %.1fs", name, timeout_seconds)
        return "Error: request timed out. Please try again or rephrase."
    except Exception as e:
        logger.exception("Tool %s failed: %s", name, e)
        return f"Error: {str(e)}"
