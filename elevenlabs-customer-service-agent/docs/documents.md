# Documentation map

This page lists **where documentation lives** in the ElevenLabs Customer Service Agent repo and what each item is for. For system behavior and APIs, follow the links below.

---

## Root

| File | Purpose |
|------|---------|
| [README.md](../README.md) | Project overview, folder layout, setup (`pip`, `uvicorn`, Docker), links to primary docs. |

---

## `docs/`: project documentation

| File | Purpose |
|------|---------|
| [getting_started.md](getting_started.md) | Step-by-step local setup: Python, Postgres, Redis, env, running the app. |
| [architecture.md](architecture.md) | End-to-end architecture: FastAPI, ElevenLabs/Twilio integration, Postgres, Redis, RAG (Milvus, MinIO), tool/agent flow. |
| [api.md](api.md) | HTTP API: health, ElevenLabs routes, RAG, tools; request/response shapes. Interactive OpenAPI at `/docs` when the server runs. |
| [database.md](database.md) | PostgreSQL schema: customers, scheduling, lookup tables, RAG/RxNorm relational tables; mirrors `app/init_db/create_tables.sql`. |
| [RAG.md](RAG.md) | RAG design for clinical/hospital use: Milvus collections, ingestion, medical terminology. |
| [RAG_RXNORM.md](RAG_RXNORM.md) | How RxNorm normalization maps to DB/Milvus and coder-style workflows. |
| [skill_loading_workflow.md](skill_loading_workflow.md) | How skills are discovered, loaded, and injected into agent context. |
| [features.md](features.md) | Feature checklist (agentic AI / job-facing); maps capabilities to files in `app/`. |
| [deploy.md](deploy.md) | AWS-oriented deployment (e.g. ECS, RDS, ElastiCache) walkthrough. |
| [Docker.md](Docker.md) | Docker Compose and container usage for local or deployed runs. |
| [system_design.md](system_design.md) | General system-design interview notes (not app-specific). |
| [hyperagents.md](hyperagents.md) | Notes on the Hyperagents / DGM paper (reference reading). |
| **documents.md** (this file) | Index of documentation and in-repo authored material. |

---

## Application code: authored docs (not in `docs/`)

These files travel with the code they describe; loaders often use them at runtime.

| Location | Purpose |
|----------|---------|
| `app/agent_configs.json` | Agent definitions, models, skills, and routing metadata for the factory/registry. |
| `app/src/agents/*/system_prompt.md` | System prompts for **customer_support_agent**, **security_agent**, **rxnorm_mapping_agent** (placeholders documented in each file). |
| `app/src/skills/*/SKILL.md` | Skill contracts: **appointment_booking**, **clinical_entity_extraction**, **email**, **rxnorm_mapping**, **text_normalize**, when to use, workflows, tool names. |

---

## Data and infrastructure scripts

| Path | Purpose |
|------|---------|
| `app/init_db/create_tables.sql` | Authoritative Postgres DDL; described in [database.md](database.md). |
| `app/init_db/seed.sql`, `app/init_db/seed.py` | Optional seed data for local/demo use. |
| `app/init_milvus.py` | Milvus collection setup (e.g. RxNorm-related collections; see `docs/RAG.md`). |

---

## Repository layout (high level)

| Area | Role |
|------|------|
| `app/main.py` | FastAPI app: lifespan (DB, Redis, Milvus, agent init), routers. |
| `app/controllers/` | HTTP routes: general API (`routes.py`), ElevenLabs (`elevenlabs_controller.py`), SendGrid (`sendgrid.py`). |
| `app/src/agents/` | Agent factory, LangGraph agents, shared tools. |
| `app/src/skills/` | Skill packages and tool scripts per skill. |
| `app/src/services/` | Dispatch, RAG, registries, DB helpers. |
| `app/src/infrastructure/` | `database`, `redis`, `milvus`, `agent` wiring. |
| `app/DAL/` | Data access (e.g. customer). |
| `tests/` | Tests and fixtures. |
| `scripts/` | Deploy and migration helpers. |

---

## Summary

- **Start here for setup:** [getting_started.md](getting_started.md) and [README.md](../README.md).  
- **Behavior and integrations:** [architecture.md](architecture.md) and [api.md](api.md).  
- **Schema:** [database.md](database.md) and `app/init_db/create_tables.sql`.  
- **Agents and skills:** `app/agent_configs.json`, `app/src/agents/*/system_prompt.md`, `app/src/skills/*/SKILL.md`, plus [skill_loading_workflow.md](skill_loading_workflow.md).  
- **RAG / clinical search:** [RAG.md](RAG.md), [RAG_RXNORM.md](RAG_RXNORM.md).
