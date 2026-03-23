# Agent infrastructure, Initialize and kill the agents (Singleton)
from src.services.agent_registry import AgentType, get_agent_registry
from typing import Dict

_agents: Dict[str, AgentType] = {}

async def init_agents() -> None:
  global _agents
  _agents_cls = get_agent_registry()
  for agent_name in _agents_cls.names():
    agent_cls = _agents_cls.get(agent_name)
    if agent_cls is not None:
      
      _agents[agent_name] = agent_cls()

async def kill_agents() -> None:
  global _agents
  for agent_name in _agents.keys():
    del _agents[agent_name]

def get_agent(agent_name: str) -> AgentType:
  return _agents[agent_name]