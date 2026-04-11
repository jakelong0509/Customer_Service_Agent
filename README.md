# Clinical Agent Hub

Clinical Agent Hub is a clinical customer-service and workflow repository centered on the `elevenlabs-customer-service-agent` application. It supports voice interactions through ElevenLabs/Twilio, email workflows, appointment and customer data in PostgreSQL, session/state caching in Redis, and clinical document retrieval with RAG infrastructure.

## Repository layout

- `elevenlabs-customer-service-agent/` - main application and project documentation
- `elevenlabs-customer-service-agent/app/` - FastAPI app, controllers, agents, skills, services, infrastructure, DB init scripts
- `elevenlabs-customer-service-agent/docs/` - architecture, API, database, RAG, deployment, and workflow docs
- `elevenlabs-customer-service-agent/tests/` - unit and integration tests

## Start here

- Project app readme: `elevenlabs-customer-service-agent/README.md`
- Documentation index: `elevenlabs-customer-service-agent/docs/documents.md`
- Setup guide: `elevenlabs-customer-service-agent/docs/getting_started.md`
- Architecture: `elevenlabs-customer-service-agent/docs/architecture.md`
- API reference: `elevenlabs-customer-service-agent/docs/api.md`
- Database schema: `elevenlabs-customer-service-agent/docs/database.md`

## What the app includes

- FastAPI service with HTTP endpoints for health checks, agent execution, and integrations
- Multi-agent / skill-based workflow structure under `app/src/agents/` and `app/src/skills/`
- PostgreSQL schema for customers, appointments, resource bookings, and clinical lookup data
- Redis for active session or transient state
- Milvus-backed clinical / RxNorm retrieval workflows documented in the RAG docs

## Local development

From `elevenlabs-customer-service-agent/app/`:

```bash
python -m venv .venv
pip install -r ../requirements.txt
uvicorn main:app --reload
```

For full environment setup, database configuration, and Docker usage, use the guides in `elevenlabs-customer-service-agent/docs/`.
