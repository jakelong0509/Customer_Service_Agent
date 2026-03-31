"""Central registry for tools used by agents.

Use the `@register_tool` decorator on tool functions so they are discoverable
at import time without manual bookkeeping.

Works with:
- LangChain's @tool decorator (returns StructuredTool)
- Plain functions
- Any callable that matches ToolType
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Iterator, Optional, List

# Tool type: any callable that can be used as a tool
# LangChain's @tool returns StructuredTool which is Callable
ToolType = Callable[..., Any]


class ToolRegistry:
    """Maps logical tool names to tool functions."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolType] = {}

    def register(self, name: str, tool_fn: ToolType) -> ToolType:
        """Register a tool by name.

        Args:
            name: Unique name for the tool
            tool_fn: The tool function or callable

        Raises:
            ValueError: If name is already registered
        """
        if name in self._tools:
            raise ValueError(
                f"Tool name {name!r} is already registered "
                f"({self._tools[name].__module__}.{self._tools[name].__qualname__})"
            )
        self._tools[name] = tool_fn
        return tool_fn

    def get(self, name: str) -> Optional[ToolType]:
        """Get a single tool by name.

        Returns the tool callable (works with LangChain @tool decorated tools).

        Example:
            tool = registry.get("search_customer")
            result = tool.invoke({"query": "john"})  # For LangChain tools
            # or
            result = tool(query="john")  # Direct call
        """
        return self._tools.get(name)

    def get_tool(self, name: str) -> ToolType:
        """Get a single tool by name, raising if not found.

        Args:
            name: Tool name to retrieve

        Returns:
            The tool callable

        Raises:
            ValueError: If tool name is not registered

        Example:
            tool = registry.get_tool("retrieve_conversation_history")
            result = await tool.ainvoke({"agent_name": "support"})
        """
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Tool {name!r} not registered (available: {self.names()})")
        return tool

    def get_tools(self, names: List[str]) -> List[ToolType]:
        """Get multiple tools by their string names.

        Args:
            names: List of tool names to retrieve

        Returns:
            List of tool callables matching the names

        Raises:
            ValueError: If any tool name is not registered

        Example:
            tools = registry.get_tools(["search_customer", "send_email"])
            # Returns [search_customer_fn, send_email_fn]
        """
        tools = []
        missing = []
        for name in names:
            tool = self._tools.get(name)
            if tool is None:
                missing.append(name)
            else:
                tools.append(tool)
        if missing:
            raise ValueError(f"Unknown tool names: {missing!r}")
        return tools

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __iter__(self) -> Iterator[str]:
        return iter(self._tools)

    def names(self) -> tuple[str, ...]:
        """Return all registered tool names."""
        return tuple(sorted(self._tools))

    def items(self) -> tuple[tuple[str, ToolType], ...]:
        """Return all registered (name, tool) pairs."""
        return tuple(sorted(self._tools.items(), key=lambda x: x[0]))

    def clear(self) -> None:
        """Remove all registrations (intended for tests)."""
        self._tools.clear()


# Default global registry instance
_default_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Get the default tool registry instance."""
    return _default_registry


def register_tool(name: Optional[str] = None, *, registry: Optional[ToolRegistry] = None):
    """Decorator to register a tool function under a stable logical name.

    If `name` is omitted, the function's ``__name__`` is used.

    Works with LangChain's @tool decorator - apply @register_tool AFTER @tool:

        from langchain.tools import tool
        from src.services.tool_registry import register_tool

        @register_tool("search_customer")
        @tool
        def search_customer(query: str) -> dict:
            '''Search for a customer by query.'''
            return {"id": 123, "name": "John"}

    Args:
        name: Optional custom name for the tool. If not provided, uses function name.
        registry: Optional custom registry. Uses default if not provided.

    Returns:
        Decorator function that registers and returns the tool.
    """

    def decorator(tool_fn: ToolType) -> ToolType:
        key = name if name is not None else tool_fn.__name__
        reg = registry if registry is not None else _default_registry
        reg.register(key, tool_fn)
        return tool_fn

    return decorator


def get_tool(name: str) -> ToolType:
    """Get a single tool by name from the default registry.

    Works with LangChain @tool decorated tools - returns the StructuredTool
    which has .invoke() and .ainvoke() methods.

    Args:
        name: Tool name to retrieve

    Returns:
        Tool callable (StructuredTool for LangChain, regular function otherwise)

    Raises:
        ValueError: If tool name is not registered

    Example with LangChain:
        from src.services.tool_registry import get_tool

        tool = get_tool("retrieve_conversation_history")
        result = await tool.ainvoke({"agent_name": "support"})

    Example with plain function:
        tool = get_tool("send_email")
        result = tool(to="john@example.com", subject="Hello")
    """
    return _default_registry.get_tool(name)


def get_tools(names: List[str]) -> List[ToolType]:
    """Get multiple tools by their string names from the default registry.

    Args:
        names: List of tool names to retrieve

    Returns:
        List of tool callables matching the names

    Raises:
        ValueError: If any tool name is not registered

    Example:
        from src.services.tool_registry import get_tools

        tools = get_tools(["search_customer", "send_email"])
        # Returns [search_customer_fn, send_email_fn]
    """
    return _default_registry.get_tools(names)
