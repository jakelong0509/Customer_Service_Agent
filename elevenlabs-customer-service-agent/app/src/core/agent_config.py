from pydantic import BaseModel
from typing import List
import json

class AgentConfig(BaseModel):
  name: str
  system_prompt: str
  llm: str
  tools: List[str]
  db_uri: str
  skill_names: List[str]

def load_agent_configs() -> List[AgentConfig]:
  with open("agent_configs.json", "r") as f:
    agent_configs = json.load(f)
  return agent_configs