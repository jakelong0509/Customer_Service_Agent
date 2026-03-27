# Skill Loading Workflow

This document describes how skills are discovered, loaded, activated, and injected into the agent context.

---

## 1. Skill Discovery

Skills are discovered from the filesystem at runtime:

**Location:** `app/src/skills/<skill_name>/SKILL.md`

Each skill is a folder containing:
- `SKILL.md` - YAML frontmatter + markdown body (required)
- `tools.py` - Skill-specific tools (optional, loaded dynamically)

### SKILL.md Format

```yaml
---
name: appointment_booking_skill
description: >-
  Voice/agent workflow for clinic-style appointment scheduling...
isolation: fork  # Optional: marks skill for isolated execution
---

# Skill Title

Procedural guidance for the agent when this skill is active...
```

**Frontmatter fields:**
- `name` - Unique skill identifier (used for activation/lookup)
- `description` - Short description shown in available skills list (Layer A)
- `isolation` - Optional flag (`fork` or `true`) for isolated execution mode

**Body content:**
- Full procedural guidance (Layer B) injected when skill is active
- Domain models, conversation flows, status values, etc.

---

## 2. Skill Registry

The `skill_registry.py` module handles skill discovery and loading:

```python
from src.skills.skill_registry import get_skills, get_skill_tools, SkillRecord

# Load skills by name
skills = get_skills(["appointment_booking_skill"])

# Load tools for active skills
skill_tools = get_skill_tools(["appointment_booking_skill"])
```

**`SkillRecord` fields:**
- `name` - Skill name from frontmatter
- `description` - Short description from frontmatter (Layer A)
- `body` - Full markdown body without frontmatter (Layer B)
- `isolation_fork` - Boolean from frontmatter `isolation` flag
- `active` - Runtime flag indicating if skill is currently active

---

## 3. Three-Layer Disclosure Model

### Layer A — Registry (Always in Context)

**Content:** For all configured skills, the system prompt includes:
- **name** - Skill identifier
- **description** - Brief description of when to use the skill

**In system prompt:**
```
## Available Skills
**appointment_booking_skill** - Voice/agent workflow for clinic-style appointment scheduling...
```

**Purpose:** The model knows what skills are available and when they apply without loading full skill documentation.

### Layer B — Skill Body (When Active)

**Content:** Full procedural guidance from `SKILL.md` body (below frontmatter).

**Activation:** The LLM calls `activate_skill` tool when it determines the skill is needed based on user intent.

**Injection:** When active, the skill body is injected into the system prompt:
```
## Current Active Skills:
**appointment_booking_skill** - # Appointment booking skill

Guidance for the agent when handling appointment scheduling...
```

### Layer C — Resources (Tools)

**Content:** Skill-specific tools loaded dynamically from `app/src/skills/<skill_name>/tools.py`.

**Loading:** Tools are loaded via `get_skill_tools(active_skill_names)` and bound to the LLM only when the skill is active.

---

## 4. Skill Activation Flow

### Initialization

1. Agent created with `skill_names` list (e.g., `["appointment_booking_skill"]`)
2. Skills loaded via `get_skills()` - all start with `active=False`
3. System prompt formatted with available skills (Layer A only)

### Runtime Activation

```python
# In skill_tools.py
@tool
async def activate_skill(skill_name: str, state: Annotated[BaseModel, InjectedState], ...):
    """Activate a skill by name."""
    skill = state.skills[skill_name]
    skill.active = True
    return Command(update={"skills": skills})
```

1. LLM sees available skills in system prompt
2. LLM determines a skill is needed based on user request
3. LLM calls `activate_skill(skill_name="appointment_booking_skill")`
4. Tool sets `skill.active = True` in state
5. On next turn, agent loads skill tools and injects skill body (Layer B)

### Deactivation

```python
@tool
async def deactivate_skill(skill_name: str, state: Annotated[BaseModel, InjectedState], ...):
    """Deactivate a skill by name."""
    skill = state.skills[skill_name]
    skill.active = False
    return Command(update={"skills": skills})
```

The LLM can deactivate skills when they are no longer needed, removing their tools and body from context.

---

## 5. System Prompt Structure

The system prompt template (`system_prompt.md`) includes:

```markdown
TODAY IS: {current_date}
CURRENT TIMEZONE: EST

---
## Available Skills
{available_skills}

---
## Current Active Skills:
{active_skills}

---

## Stored context (hints, not ground truth)
{learned_instruction}
```

**Formatting at runtime** (in `agent()` method):

```python
system_prompt.format(
    current_date=datetime.now().strftime("%Y-%m-%d"),
    available_skills="\n".join([
        f"**{skill.name}** - {skill.description}"
        for skill in self.skills.values() if not skill.active
    ]),
    active_skills="\n".join([
        f"**{skill.name}** - {skill.body}"
        for skill in self.skills.values() if skill.active
    ]),
    learned_instruction=instruction
)
```

---

## 6. Tool Binding

Tools are bound to the LLM dynamically based on active skills:

```python
# Base tools always available
self.base_tools = [activate_skill, deactivate_skill, ...]

# Skill tools loaded when skills are active
active_skill_names = [skill.name for skill in self.skills.values() if skill.active]
self.skill_tools = get_skill_tools(active_skill_names)

# Bind all available tools
response = self.llm.bind_tools(self.base_tools + self.skill_tools).invoke(messages)
```

---

## 7. Isolated Skills (Future)

Skills marked with `isolation: fork` in frontmatter can be executed in isolated contexts:

1. **Child run:** Fresh message list with only that skill's Layer B + tools
2. **Parent thread:** Receives structured summary, not full child trace
3. **Implementation:** Separate graph invocation with its own `thread_id`

Current implementation supports the flag; full isolation mechanism is pending.

---

## 8. State Management

Skill state persists across turns in `CustomerSupportAgentState`:

```python
class CustomerSupportAgentState(BaseModel):
    messages: Annotated[list, add_messages]
    skills: dict[str, SkillRecord]  # Keyed by skill name
```

The `skills` dictionary maintains:
- Which skills are configured for this agent
- Which skills are currently active
- Full skill content (name, description, body)

State is preserved by LangGraph's checkpointer across conversation turns.

---

## 9. Implementation Checklist

- [x] Skills stored in `app/src/skills/<skill_name>/SKILL.md`
- [x] YAML frontmatter with `name`, `description`, optional `isolation`
- [x] `skill_registry.py` for discovery and loading
- [x] `SkillRecord` with `active` runtime flag
- [x] System prompt with `{available_skills}` and `{active_skills}` placeholders
- [x] `activate_skill` and `deactivate_skill` tools
- [x] Dynamic tool binding based on active skills
- [x] Agent state tracks active skills across turns
- [ ] Skill-specific tools in `app/src/skills/<skill_name>/tools.py`
- [ ] Isolated skill execution (fork mechanism)
- [ ] Skill action summarization (capture key outcomes before deactivation for learned_instruction)

---

## 10. Summary

| Aspect | Implementation |
|--------|----------------|
| **Discovery** | Filesystem scan of `src/skills/*/SKILL.md` at runtime |
| **Layer A** | Always in context: name + description from frontmatter |
| **Layer B** | Injected when skill active: full `SKILL.md` body |
| **Layer C** | Tools loaded dynamically when skill active |
| **Activation** | LLM calls `activate_skill` tool based on user intent |
| **Deactivation** | LLM calls `deactivate_skill` when skill no longer needed |
| **State** | `skills` dict in `CustomerSupportAgentState` with `active` flags |
| **Isolation** | Frontmatter flag supported; full fork mechanism pending |
