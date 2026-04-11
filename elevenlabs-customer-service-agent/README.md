# Clinical Agent Hub

Clinical Agent Hub is a FastAPI-based clinical customer-service application with voice and workflow integrations, multi-agent orchestration, scheduling data in PostgreSQL, session/state caching in Redis, and clinical retrieval pipelines backed by Milvus.

## Structure

- `app/` - main application code: controllers, agents, skills, services, infrastructure, DB init scripts
- `tests/` - unit and integration tests
- `scripts/` - deploy and migration helpers
- `docs/` - architecture, API, database, RAG, deployment, and workflow documentation

## Quick start

1. Copy `.env.example` to `.env` and set your credentials.
2. Create and activate a virtual environment.
3. Install dependencies with `pip install -r requirements.txt`.
4. Start locally with `uvicorn app.main:app --reload`.
5. Or run with Docker / Compose if preferred.

## Core capabilities

- Voice-oriented integrations for ElevenLabs / Twilio flows
- Multi-agent and skill-based workflow execution
- Customer, appointment, provider, and booking data in PostgreSQL
- Redis-backed temporary state and session support
- Clinical RAG and RxNorm-related retrieval workflows

## Docs

- [Documentation map](docs/documents.md)
- [Getting started](docs/getting_started.md)
- [Architecture](docs/architecture.md)
- [API](docs/api.md)
- [Database](docs/database.md)
- [RAG](docs/RAG.md)
