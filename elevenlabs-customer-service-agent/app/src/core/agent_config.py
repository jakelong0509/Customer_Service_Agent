from pydantic import BaseModel
from typing import List
import json
import os
from pathlib import Path
class AgentConfig(BaseModel):
  name: str
  system_prompt: str
  llm: str
  tools: List[str]
  db_uri: str
  skill_names: List[str]

def load_agent_configs() -> List[AgentConfig]:
  config_path = Path(__file__).parent.parent.parent / "agent_configs.json"
  with open(config_path, "r") as f:
    return json.load(f)
