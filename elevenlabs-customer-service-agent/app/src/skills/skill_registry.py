"""Discover skills from ``src/skills/*/SKILL.md`` (YAML frontmatter + markdown body).

This module lives under ``src/.skills/``. The skills **content** root is the sibling
directory ``src/skills/`` (one folder per skill, each with a ``SKILL.md``).

Because a leading-dot folder is not a normal Python package name, import this file via
``importlib`` or a thin re-export under ``src/skills/`` if you need ``from src...``.

Public API:
  - ``list_skills()`` — metadata for routing and prompt tables
  - ``get_skill(skill_id)`` — resolve by frontmatter ``name`` or by folder name
  - ``load_skill_body(skill_id)`` — markdown body without frontmatter (for ``{skill_workflow}``)
  - ``render_skills_markdown_table()`` — pipe into system prompt ``## Skills`` section
"""

from __future__ import annotations

from abc import ABC
from pathlib import Path
from typing import Any, Mapping, NamedTuple, List, Callable
import importlib
import frontmatter
import inspect
from pydantic import BaseModel, Field
from typing import Annotated

# ``src/.skills/`` -> parent is ``src/`` -> skills live in ``src/skills/``
_SKILLS_ROOT = str(Path.cwd() / "src/skills/")
print(f"Skills root: {_SKILLS_ROOT}")

class SkillRecord(BaseModel):
    """One skill discovered on disk."""
    name: Annotated[str, Field(description="The name of the skill")]
    description: Annotated[str, Field(description="The description of the skill")]
    isolation_fork: Annotated[bool, Field(description="Whether the skill is isolated")]
    body: Annotated[str, Field(description="The body of the skill")]
    active: bool = False


def _parse_skill_md(path: Path, skill_folder_name: str) -> SkillRecord:
  with path.open(encoding="utf-8-sig") as f:
      post = frontmatter.load(f)
  meta = post.metadata
  if meta is None:
      meta = {}
  if not isinstance(meta, dict):
      raise ValueError(f"Skill frontmatter must be a mapping, got {type(meta).__name__}: {path}")
  body = post.content if post.content is not None else ""
  skill_record = SkillRecord(
    name=meta.get("name"),
    description=meta.get("description"),
    isolation_fork=meta.get("isolation") == "fork" or meta.get("isolation") is True,
    body=body,
  )
  return skill_record


def get_skills(skill_names: List[str]) -> dict[str, SkillRecord]:
  skills: dict[str, SkillRecord] = {}
  for skill_name in skill_names:
    path = Path(_SKILLS_ROOT + "/" +skill_name + "/SKILL.md")
    print(f"Skill path: {path}")
    if not path.exists():
      raise FileNotFoundError(f"Skill {skill_name} not found")
    skills[skill_name] = _parse_skill_md(path, skill_name)
  return skills

def get_skill_tools(skill_names: List[str]) -> List[Callable]:
  tools: List[Callable] = []
  for skill_name in skill_names:
    mod = importlib.import_module(f"src.skills.{skill_name}.scripts.tools")
    tools.extend(mod.get_tools())
  return tools



