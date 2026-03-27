# Skill loading workflow

This document covers how skills are discovered, triggered, loaded into the model context, kept or trimmed, and optionally isolated.

---

## 1. Where loading happens

Each turn, the support agent builds a **system message** before calling the LLM. Skill loading is the step that decides **whether** full skill text is present and **what** text is injected (registry vs full `SKILL.md` body vs lazy resources). Today the prompt template reserves `{{skill_name}}` and `{{skill_workflow}}`; wiring those values in `agent()` completes the loader.

---

## 2. Progressive disclosure (three layers)

### Layer A — Registry (always in context)

- **Content:** Per enabled skill: **name**, **short description**, optional flags (e.g. `isolation: fork` in frontmatter).
- **In repo:** Skills table in `system_prompt.md`, kept in sync with each skill’s `SKILL.md` YAML `name` / `description`.
- **Purpose:** The model or a router can tell that a skill exists and when it applies **without** loading the full document.

### Layer B — Skill body (after trigger)

- **Content:** Procedural guidance below the frontmatter in `SKILL.md`.
- **Trigger:** Router (rules, keywords, slash command, or small classifier) chooses zero or one **primary** skill for the turn.
- **Injection:** Read `SKILL.md`, map body → `{{skill_workflow}}`, canonical name → `{{skill_name}}` in the system prompt section **Skill Workflow**.

### Layer C — Resources (lazy)

- **Content:** Files beside `SKILL.md` (e.g. `tools.py`, snippets).
- **Rule:** Load into context **only** when `SKILL.md` says to, or when the loader explicitly attaches an excerpt.

---

## 3. System prompt sections relevant to skills

| Section | Role for skills |
|---------|------------------|
| **Skill registry** | Always-on index (Layer A). |
| **Skill Workflow** (`{skill_name}`, `{skill_workflow}`) | Holds Layer B when a skill is **hot**; empty or placeholder when none. |
| **Global policy** (rest of system prompt) | Not skill text; should not be “swapped out” when toggling skills—only the workflow block changes. |

Avoid replacing the entire system prompt when loading a skill; update the **workflow** (and optionally tool bindings for isolated runs) instead.

---

## 4. Compaction and skill lifecycle

Long threads add tool messages and repeated skill text. **Compaction** (summarize or drop middle context when approaching a token threshold) should:

- **Keep:** Skill **registry** (names + descriptions).
- **Keep:** Recent turns needed to continue the task.
- **Trim or summarize:** Full `{skill_workflow}` once the router marks the skill **inactive** (e.g. after *K* turns without use or when another skill is selected).
- **Not remove without a substitute:** Global policy; registry.

A skill need not unload the instant the user changes topic; defer dropping Layer B until the next compaction pass so answers stay coherent.

---

## 5. Isolated skills (fork / subagent)

For skills that would dominate or pollute the main thread:

1. Declare in `SKILL.md` frontmatter (convention), e.g. `isolation: fork`.
2. **Child run:** Fresh message list; system = global policy + **only** that skill’s Layer B (+ Layer C if needed). No parent history unless you pass a short brief.
3. **Parent thread:** Receives a **short structured summary** only, not the child’s full trace.

Implement as a separate graph invocation or agent with its own `thread_id` so the main conversation’s skill stack stays clean.

---

## 6. Skill-scoped tools (optional)

When a skill is isolated or explicitly “exclusive,” you may bind **only** the tools that skill requires for that run. Precedence for multiple active skills (stack vs last-wins) should be documented in your router to avoid conflicting Layer B instructions.

---

## 7. Persistence of skill-related state

What must survive across turns (same call) is usually enough for skill loading:

- **Active skill id** (or stack) and **last compaction summary** can live in graph state or a small store keyed by conversation id.
- The LangGraph **checkpointer** carries message history, which indirectly affects when the router re-triggers a skill; durable checkpointers are only relevant to skill loading insofar as they preserve **which skill was active** if you persist that in state.

No requirement to document customer stores or HTTP here—they are outside skill loading.

---

## 8. Implementation checklist (skill loading only)

1. Sync **registry** in `system_prompt.md` with every `SKILL.md` frontmatter `name` / `description`.
2. Implement **router** → `none` or `skill_id` per turn.
3. On trigger, **load** `app/src/skills/<folder>/SKILL.md` and fill `{skill_name}` / `{skill_workflow}` in `agent()`.
4. **Lazy Layer C** only when the skill doc or loader says so.
5. **Compaction policy** for dropping or summarizing Layer B when inactive; always keep registry.
6. **Isolation path** for flagged skills: child run + summary merge.
7. **Persist** active skill metadata in conversation state if the router needs it after compaction.

---

## 9. Summary

| Mode | Skill loading behavior |
|------|-------------------------|
| Standard | Registry always; Layer B injected when triggered; removed or summarized on compaction when inactive. |
| Isolated | Layer B (+ C) in a child context; parent sees summary only. |
| Registry | Never dropped by compaction; only descriptions, not full `SKILL.md`. |
