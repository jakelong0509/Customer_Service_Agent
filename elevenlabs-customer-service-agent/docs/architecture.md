# Architecture: Clinical Agent Hub (voice + email + RAG)

## Overview

**Clinical Agent Hub** is a **FastAPI** backend for **voice** (ElevenLabs / Twilio webhooks) and **email** (SendGrid Inbound Parse). It runs **LangGraph-style agents** defined in `app/agent_configs.json`, composed with **skills** (appointment booking, email, text normalization, clinical entity extraction, RxNorm mapping). Persistence uses **PostgreSQL**; **Redis** is initialized for call-scoped state; **Milvus** (often **Zilliz Cloud**) backs **semantic search / RAG** used inside skills (e.g. RxNorm concept search via `RAGService`).

**Key Capabilities:**
- **ElevenLabs:** resolve or create customer by phone → run or end agent (`invoke_agent` → registered agent `arun`)
- **SendGrid:** `POST /api/sendgrid/inbound` (multipart); heavy agent work should move to **RabbitMQ workers** (today may use **FastAPI `BackgroundTasks`** as a bridge)
- Customer and **scheduling** data in PostgreSQL (`customers`, `provider_names` / `providers`, `slot_templates`, `appointments`, `appointment_resource_bookings`, `general_statuses`, `callback_requests`, plus clinical/RxNorm tables — see `docs/database.md`)
- **Redis** client (`src/infrastructure/redis.py`) for call/session keys; full “active call” flows may evolve with product
- **Milvus / Zilliz:** vector collections (e.g. RXNCONSO in Milvus; relational RxNorm tables in Postgres) — ingestion scripts live under `app/init_milvus.py` and `RAG_service`
- **RabbitMQ (target):** message broker for **heavy, asynchronous work** decoupled from the HTTP layer

---

## Current Architecture (Phase 1: 100 calls/day)

```
┌────────────────────────────┐     ┌──────────────────────────────┐
│  ElevenLabs / Twilio       │     │  SendGrid Inbound Parse      │
│  (voice webhooks)          │     │  POST /api/sendgrid/inbound  │
└─────────────┬──────────────┘     └──────────────┬───────────────┘
              │ HTTPS                            │ HTTPS
              └──────────────────┬───────────────┘
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│  FastAPI — app/main.py                                         │
│  Routers: app/controllers/routes.py                            │
│           app/controllers/elevenlabs_controller.py             │
│           app/controllers/sendgrid.py                          │
│  Lifespan: init_milvus → init_pool → init_redis → create_agent │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  GET  /api/health                                        │  │
│  │  GET  /api/elevenlabs/customer/{phone}                   │  │
│  │  POST /api/elevenlabs/agent/run   → invoke_agent        │  │
│  │  POST /api/elevenlabs/agent/end   → invoke_agent        │  │
│  │  POST /api/sendgrid/inbound       → BackgroundTasks / MQ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                   │
│  ┌─────────────────────────┼─────────────────────────────────┐   │
│  │  Agents & skills       │  src/services/, src/agents/    │   │
│  │  agent_configs.json    │  skill_registry, dispatch_agent │   │
│  └─────────────────────────┼─────────────────────────────────┘   │
│                            │                                   │
│  ┌─────────────────────────┼─────────────────────────────────┐ │
│  │         Data Layer      │                                 │ │
│  │  ┌──────────┐  ┌───────┴──┐  ┌──────────┐                 │ │
│  │  │PostgreSQL│  │  Redis   │  │ Milvus   │                 │ │
│  │  │(Primary) │  │(client + │  │(Zilliz / │                 │ │
│  │  │scheduling│  │ call keys)│  │ vectors) │                 │ │
│  │  │+ RxNorm   │  │          │  │ RAGService│                 │ │
│  │  │  caches   │  │          │  │ in skills │                 │ │
│  │  └──────────┘  └──────────┘  └──────────┘                 │ │
│  │  ┌──────────┐  ┌──────────────────────────────────────┐   │ │
│  │  │ RabbitMQ │  │  Worker processes (target / scaling)  │   │ │
│  │  │ (queues) │  │  Separate from uvicorn                │   │ │
│  │  └──────────┘  └──────────────────────────────────────┘   │ │
│  └───────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. HTTP API (`app/controllers/`)

Routers are mounted from `app/main.py` (working directory is `app/` when running `uvicorn`).

| Endpoint | Handler | Purpose |
|----------|---------|---------|
| `GET /` | `main.py` | Service id + pointer to OpenAPI `/docs` |
| `GET /api/health` | `controllers/routes.py` | Liveness / readiness |
| `GET /api/elevenlabs/customer/{caller_phone_number}` | `elevenlabs_controller.py` | Load or create `CustomerModel` by phone |
| `POST /api/elevenlabs/agent/run` | `elevenlabs_controller.py` | Run agent (`ElevenLabsAgentRunRequest` → `invoke_agent`) |
| `POST /api/elevenlabs/agent/end` | `elevenlabs_controller.py` | End-of-call agent invocation (same dispatch path) |
| `POST /api/sendgrid/inbound` | `sendgrid.py` | SendGrid Inbound Parse (multipart form); schedules agent work (`BackgroundTasks` today; RabbitMQ later) |

There is **no** standalone `POST /api/tools/run` or `POST /api/rag/query` router in the current tree. **RAG** runs **inside** services and skills (`RAGService`, RxNorm skill tools), not as a separate public HTTP RAG endpoint unless you add one.

**Typical voice flow:**
```
ElevenLabs → GET /api/elevenlabs/customer/{phone}
          → POST /api/elevenlabs/agent/run
                Body: ElevenLabsAgentRunRequest
                  (agent_name, request, call_sid, caller_phone_number, email_metadata, ...)
                     ↓
            CustomerDA → customer row
                     ↓
            invoke_agent(agent_name, body, customer, call_sid)
                     ↓
            Agent class .arun(...)  (LangGraph / AgentBase)
                     ↓
            AgentRunResponse { result, is_error }
```

### 2. Database Layer

#### PostgreSQL (Primary Data Store)

**Scheduling & CRM (authoritative DDL: `app/init_db/create_tables.sql`):**
- `customers`, `provider_names`, `providers`, `slot_templates`, `general_statuses`, `appointments`, `appointment_resource_bookings`, `callback_requests`

**Clinical / RxNorm (relational cache in Postgres; RXNCONSO vectors in Milvus):**
- `clinical_note_embeddings`, `umls_concepts`, `rxnorm_relationships`, `rxnorm_attributes`, `rxnorm_semantic_types`, `rxnorm_documentation`, `drug_interactions`

There is **no** `tool_logs` or `documents` table in the current `create_tables.sql`. Full column lists and indexes: **`docs/database.md`**.

**Why PostgreSQL:**
- ACID compliance for transactions
- JSONB for flexible logs
- Full-text search (backup for RAG)
- Mature, well-understood

#### Redis (session / call-scoped state)

**Implementation:** `src/infrastructure/redis.py` — async client, initialized in `main.py` lifespan. Helpers such as `get_call_state` / `set_call_state` support **per-`call_sid`** keys with TTL.

**Intended use:** fast ephemeral state during voice or multi-step flows (conversation/thread hints, lightweight caches). Customer-of-record remains **PostgreSQL**.

**Why Redis:**
- Low-latency key/value for active-session data
- TTL-based expiry without manual cleanup in many cases

#### RabbitMQ (message broker)

**Role:** Hold **jobs/messages** between “the HTTP request accepted work” and “a worker finished processing.” This is **not** Redis: RabbitMQ is the **queue**, Redis remains **session/cache**.

**Why RabbitMQ (vs in-process `BackgroundTasks` only):**
- **Durability:** Messages survive API process restarts and deploys (within broker configuration).
- **Backpressure:** Bursts (e.g. many SendGrid inbound webhooks) **queue** instead of piling unbounded heavy agent work in one API process.
- **Horizontal scaling:** Multiple API replicas **publish** to the same queues; **worker** processes (separate containers/hosts) **consume** at a controlled concurrency.
- **Retries / DLQ:** Failed handling can be retried or routed to a **dead-letter queue** for inspection.

**Typical flow (inbound email → agent):**
```
SendGrid POST /api/sendgrid/inbound
       │
       ▼
FastAPI validates, builds payload ── publish ──▶ RabbitMQ (exchange → queue)
       │
       ▼
HTTP 200 (acknowledge webhook quickly)
       
       ... async ...

Worker process ── consume message ──▶ run agent / tools ──▶ ack or nack
```

**Implementation options:** **Celery** with RabbitMQ as broker, **Kombu**, **aio-pika** / **pika**, or another AMQP client—broker choice is **RabbitMQ**; worker code lives in **separate processes** from `uvicorn`.

**Note:** Until workers are deployed, the app may still use **FastAPI `BackgroundTasks`** as a stepping stone; production-scale, multi-replica setups should **publish to RabbitMQ** instead of relying on in-process background tasks alone.

#### Milvus (vector database — Zilliz Cloud compatible)

**Client:** `src/infrastructure/milvus.py` — `MilvusClient`, `init_milvus()` at startup. Configure with **`MILVUS_CLUSTER_ENDPOINT`** (include **`:443`** for Zilliz HTTPS URLs) and **`MILVUS_COLLECTION_TOKEN`**. If unset, `init_milvus()` skips connection (skills that need Milvus will require it).

**RAG in this repo:** `src/services/RAG_service.py` embeds text (e.g. HuggingFace / PubMedBERT-style models in ingestion scripts), ingests **RRF** / structured files into collections, and runs **hybrid / semantic search** used from skill code (notably **RxNorm** flows in `rxnorm_mapping_skill`).

**Typical pipeline (ingestion):**
```
RxNorm RRF / exports → ingest_local / DB ingest (init_milvus.py, db_service)
                    → embeddings → Milvus collections (e.g. RXNCONSO)
                    → relational rows → PostgreSQL (RXNREL, RXNDOC, …)
```

**Query path (runtime):** Skill tools call `RAGService` → Milvus search → results to the agent.

**Why Milvus:**
- Built for billion-scale vector search; fits clinical term / concept retrieval

#### Object storage (optional, not in current `app/` tree)

**S3-compatible storage (e.g. MinIO)** is a common addition for **raw uploads** (PDFs, images) before extraction. This repository does **not** yet include a MinIO client module; ingestion examples use **local file paths** (see `init_milvus.py`). Add object storage when you implement a full document-upload pipeline.

---

## Agents and skills (not a legacy “tool registry” HTTP layer)

**Configuration:** `app/agent_configs.json` lists agents with `system_prompt_path`, `llm`, `skill_names`, `communication_type` (`voice` | `email` | `chat`), and optional `state_class`.

**Runtime:** `src/services/agent_registry.py` + `src/agents/agent_factory.py` build **LangGraph** agents. `invoke_agent` in `src/services/dispatch_agent.py` resolves `get_agent(agent_name)` and calls **`await agent.arun(request, customer, session_id)`**.

**Registered agents (from config):**
| Agent name | Role (summary) |
|------------|------------------|
| `customer_support_agent` | Voice; skills: appointment, email |
| `customer_support_agent_email` | Email; appointment skill |
| `security_agent` | Security / verification (`SecurityAgentState`) |
| `rxnorm_mapping_agent_email` | Email; text normalize → clinical entities → RxNorm + Milvus |

**Shared tools (memory / skills):** `activate_skill`, `deactivate_skill`, `retrieve_conversation_history`, `store_conversation_history`, `store_session_outcome`, `find_similar_sessions` — see `src/agents/shared_tools/`.

**Skills:** `app/src/skills/*/` — each has `SKILL.md` and `scripts/tools.py` (e.g. `appointment_booking_skill`, `email_skill`, `text_normalize_skill`, `clinical_entity_extraction_skill`, `rxnorm_mapping_skill`).

---

## RAG (Retrieval-Augmented Generation) Flow

### Ingestion (as implemented)

Batch / operator-driven flows use **`app/init_milvus.py`** and **`RAGService.ingest_local`** to read **RRF** (or similar) files, embed with the configured embedding model, and load **Milvus** collections. **`db_service`** can load companion rows into **PostgreSQL** for relational joins and SQL filters.

### Query flow (runtime)

There is **no** dedicated **`POST /api/rag/query`** route. Retrieval happens **inside agent turns** when a **skill** calls **`RAGService`** (e.g. semantic search over **RXNCONSO** or related collections in **`rxnorm_mapping_skill`**).

```
User message (voice or email)
       │
       ▼
  POST …/agent/run  or  email pipeline
       │
       ▼
  invoke_agent → agent + active skills
       │
       ▼
  Skill tool → RAGService → Milvus (± Postgres for RXNREL / RXNDOC / …)
       │
       ▼
  Model uses retrieved rows in its reply
```

---

## Handling Long Operations (30+ seconds)

**Problem:** Some tools (e.g. heavy integrations, batch eligibility checks) take >30s
**Solution:** Async pattern with ElevenLabs conversation management

```
Scenario: A long-running agent or tool step (e.g. external API) takes minutes

ElevenLabs                    Our API
──────────                    ───────
   │                             │
   │──POST /api/elevenlabs/agent/run ▶│
   │  { agent_name, request, … }  │
   │                             │
   │◀───Immediate Response──────│
   │  {"result": "Processing...", │
   │   "is_async": true,         │
   │   "job_id": "job-123"}      │
   │                             │
   │                             │──┐
   │                             │  │ Background Worker
   │                             │◀─┘ Complete job
   │                             │
   │──Polling GET /jobs/job-123─▶│
   │◀───{"status": "complete",    │
   │     "result": "Done"}       │
   │                             │
   │──Continue conversation─────▶│
```

**Implementation:**
- **Broker:** **RabbitMQ** for durable queues and worker consumption (see [RabbitMQ (message broker)](#rabbitmq-message-broker)).
- **Workers:** Separate processes that consume from RabbitMQ and execute long tasks (agents, integrations). Scale workers independently of the API.
- **Low volume / dev:** In-process `BackgroundTasks` may suffice; **multiple API replicas** or **heavy agents** should use RabbitMQ.
- **Optional:** PostgreSQL table `async_jobs` (or equivalent) to expose **job_id** status to callers when the product needs polling.

---

## Security & Access Control

### Document Security (RAG)

Future hardening often adds a **`documents`** (or similar) table with **tenant / company id**, **object-store path**, and **access level**, and restricts Milvus metadata queries accordingly. **That table is not in the current `create_tables.sql`.** Implement when you add user-visible document upload and multi-tenant RAG.

### Authentication
- **ElevenLabs / SendGrid** webhooks should be **locked down** in production (e.g. verify SendGrid signatures, IP allowlists, secrets for internal routes) — tighten per your threat model
- **Rate limiting** on public endpoints as traffic grows

---

## Monitoring & Observability

**Metrics to Track:**
| Metric | Tool | Alert Threshold |
|--------|------|-----------------|
| API response time | CloudWatch/Datadog | p99 > 500ms |
| Tool execution time | Custom | > 10 seconds |
| PostgreSQL connections | PostgreSQL | > 80% max |
| Redis memory usage | Redis | > 85% |
| Milvus query latency | Milvus | > 200ms |
| RabbitMQ queue depth / consumer lag | RabbitMQ | Sustained growth / lag above SLO |
| Error rate | Application | > 1% |

**Logging Strategy:**
- Application logs → your log aggregator (e.g. CloudWatch, Datadog)
- Optional: persist agent or audit trails in PostgreSQL when you add tables for that purpose
- Access logs from load balancer when deployed behind ALB/API gateway

---

## Phase 2: Growth Architecture (1,000+ calls/day)

When you hit higher scale, add:

```
┌─────────────────────────────────────────┐
│         Cloud Load Balancer (L7)      │
│    - SSL termination                  │
│    - Health checks                    │
│    - Rate limiting                    │
└───────────────────┬─────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   ┌────────┐  ┌────────┐  ┌────────┐
   │API Srv 1│  │API Srv 2│  │API Srv N│
   └────┬───┘  └────┬───┘  └────┬───┘
        │           │           │
        └───────────┼───────────┘
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
┌─────────┐  ┌──────────┐  ┌──────────┐
│PostgreSQL│  │  Redis   │  │  Milvus  │
│Primary  │  │ Sentinel │  │  Cluster │
│+ Replica│  │ (HA)     │  │          │
└─────────┘  └──────────┘  └──────────┘
                    │
              ┌─────┴─────┐
              ▼           ▼
         ┌────────┐  ┌────────────┐
         │ S3 /   │  │ RabbitMQ   │
         │MinIO   │  │ (broker)   │
         │(opt.)  │  │            │
         └────────┘  └─────┬──────┘
                         │
                         ▼
                   ┌───────────┐
                   │  Workers  │
                   │ (consumers)│
                   └───────────┘
```

**Additions:**
- Load balancer for high availability
- Redis Sentinel for HA
- PostgreSQL read replica
- **RabbitMQ** (HA cluster or managed service) for job queuing
- **Worker** processes consuming from RabbitMQ (scale independently of API)

---

## Folder structure (actual layout)

```
app/
├── main.py                 # FastAPI app, lifespan, router includes
├── agent_configs.json      # Agent definitions (skills, prompts, LLM)
├── controllers/            # HTTP routers
│   ├── routes.py           # GET /api/health
│   ├── elevenlabs_controller.py
│   └── sendgrid.py
├── src/
│   ├── agents/             # agent_factory, per-agent prompts/state
│   ├── core/               # config, customer models, agent run requests
│   ├── infrastructure/     # database, redis, milvus
│   ├── services/           # agent_registry, dispatch_agent, RAG_service, skill_registry, db_service
│   ├── skills/             # SKILL.md + scripts per skill
│   └── utils/
├── DAL/                    # e.g. customerDA
├── init_db/                # create_tables.sql, seeds
└── init_milvus.py          # Milvus / DB ingestion helpers (operator scripts)
```

---

## Environment variables (aligned with `src/core/config.py`)

```bash
# PostgreSQL — asyncpg URL (either name works in Settings)
DATABASE_URL=postgresql://user:pass@localhost:5432/customer_service
POSTGRES_CONNECTION_STRING=postgresql://user:pass@localhost:5432/customer_service

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_USERNAME=optional
REDIS_PASSWORD=optional

# Milvus / Zilliz — public endpoint, include :443 for HTTPS serverless
MILVUS_CLUSTER_ENDPOINT=https://in03-xxxxx.cloud.zilliz.com:443
MILVUS_COLLECTION_TOKEN=your_zilliz_token_or_user_password

# RabbitMQ (when you add publishers/consumers)
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# App
LOG_LEVEL=INFO
ENVIRONMENT=development
```

Embedding models and API keys for LLMs are typically set via **environment** or your agent factory; see `agent_configs.json` and deployment secrets. **MinIO** variables are not used by the current codebase until you add an object-storage client.

---

## Summary

This architecture supports:
- **Voice** flows via **ElevenLabs** routes and **LangGraph** agents + skills
- **Email** flows via **SendGrid** inbound webhook (scale-out path: **RabbitMQ** + workers)
- **PostgreSQL** for CRM, scheduling, and RxNorm **relational** tables; **Milvus** for **RXNCONSO** (and related) vectors consumed through **`RAGService`**
- **Clear upgrade path:** load-balanced APIs, Redis HA, RabbitMQ cluster, worker pools

**Key Decisions:**
- ✅ **PostgreSQL:** Single source of truth for relational data (see `docs/database.md`)
- ✅ **Redis:** Initialized for session/call keys (`src/infrastructure/redis.py`)
- ✅ **Milvus / Zilliz:** Vector search for skill-driven RAG (config via `MILVUS_*`)
- ✅ **RabbitMQ (target):** Offload heavy async work from `uvicorn` processes
- ✅ **No MinIO in repo yet:** add when implementing upload + extraction pipelines
- ✅ **Agents + skills** (`invoke_agent` / LangGraph) instead of a standalone **`POST /api/tools/run`** tool registry

**Next Steps:**
1. Harden **SendGrid** and **ElevenLabs** webhook security (signatures, auth, rate limits)
2. **RabbitMQ:** publish on inbound email; worker process consuming and running `invoke_agent`
3. Monitoring: API latency, **Milvus** errors, **Postgres** pool, **RabbitMQ** depth, agent failure rate
4. Optional: generic **document upload** pipeline + tenant-aware RAG tables when product requires it
