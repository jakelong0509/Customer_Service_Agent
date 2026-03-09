# Tool dispatch — run agent tools with context, timeout, optional concurrency limit
import asyncio
import json
import logging
from typing import Any

from app.models.conversation import CallContext
from app.tools.registry import run as registry_run

logger = logging.getLogger(__name__)

# Max concurrent tool executions per process (optional)
TOOL_SEMAPHORE: asyncio.Semaphore | None = None  # set to asyncio.Semaphore(5) to limit


async def dispatch(
    tool_name: str,
    arguments: dict[str, Any] | str,
    context: CallContext,
    *,
    timeout_seconds: float = 30.0,
) -> str:
    """
    Run a tool by name with the given arguments and call context.
    arguments: dict or JSON string (parsed to dict).
    Returns a string result for the agent (tool_result payload).
    """
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments) or {}
        except json.JSONDecodeError:
            arguments = {}
    if not isinstance(arguments, dict):
        arguments = {}
    result = await registry_run(
        tool_name,
        arguments,
        context,
        timeout_seconds=timeout_seconds,
        semaphore=TOOL_SEMAPHORE,
    )
    if isinstance(result, dict):
        return json.dumps(result)
    return str(result)
