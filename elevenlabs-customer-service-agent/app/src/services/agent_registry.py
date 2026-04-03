"""Central registry for agent classes defined under `agents/`.

Use the `@register_agent` decorator on agent classes so they are discoverable
at import time without manual bookkeeping.
"""
from __future__ import annotations

from typing import Any, Dict, Iterator, Optional, Type, List
from src.core.agent_base import AgentBase
from src.agents.agent_factory import AgentFactory
import json
from src.core.agent_config import AgentConfig, load_agent_configs
from pathlib import Path
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
load_dotenv()

# Agent implementation type: any class used as an agent (subclassing optional).
AgentType = Type[AgentBase]
AGENTS = {}

class AgentRegistry:
    """Maps logical agent names to agent classes."""

    def __init__(self) -> None:
        self._agents: Dict[str, AgentType] = {}

    def register(self, name: str, agent_cls: AgentType) -> AgentType:
        if name in self._agents:
            raise ValueError(
                f"Agent name {name!r} is already registered "
                f"({self._agents[name].__module__}.{self._agents[name].__qualname__})"
            )
        self._agents[name] = agent_cls
        return agent_cls

    def get(self, name: str) -> Optional[AgentType]:
        return self._agents.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._agents

    def __iter__(self) -> Iterator[str]:
        return iter(self._agents)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._agents))

    def items(self) -> tuple[tuple[str, AgentType], ...]:
        return tuple(sorted(self._agents.items(), key=lambda x: x[0]))

    def clear(self) -> None:
        """Remove all registrations (intended for tests)."""
        self._agents.clear()


_default_registry = AgentRegistry()


def get_agent_registry() -> AgentRegistry:
    return _default_registry


def register_agent(name: Optional[str] = None, *, registry: Optional[AgentRegistry] = None):
    """
    Decorator to register an agent class under a stable logical name.

    If `name` is omitted, the class's ``__name__`` is used.

    Example (in ``agents/my_agent.py``)::

        from app.services.agent_registry import register_agent

        @register_agent("support")
        class SupportAgent:
            ...
    """

    def decorator(agent_cls: AgentType) -> AgentType:
        key = name if name is not None else agent_cls.__name__
        reg = registry if registry is not None else _default_registry
        reg.register(key, agent_cls)
        return agent_cls

    return decorator


def create_agent() -> AgentFactory:
  agent_configs = load_agent_configs()
  for agent_config in agent_configs:
    system_prompt = Path(Path(__file__).parent.parent.parent / agent_config["system_prompt_path"]).read_text()
    llm = ChatOpenAI(model=agent_config["llm"], base_url="https://api.moonshot.ai/v1", temperature=0.6, max_tokens=25000, timeout=None, max_retries=2, extra_body={
        "thinking": {"type": "disabled"}
    })
    db_uri = os.getenv(agent_config["db_uri"])
    agent_cls = AgentFactory(
      system_prompt=system_prompt,
      name=agent_config["name"],
      llm=llm,
      tools=agent_config["tools"],
      db_uri=db_uri,
      skill_names=agent_config["skill_names"],
    )
    AGENTS[agent_config["name"]] = agent_cls

def get_agent(name: str) -> AgentFactory:
  return AGENTS[name]

def get_agent_names() -> List[str]:
  return list(AGENTS.keys())