# AI Clinical Support Agent - Multichannel Voice & Email

A production grade, multichannel AI customer service system built with **LangGraph agents**, **ElevenLabs voice AI**, and **SendGrid email**. Handles realtime voice calls and inbound email through a unified agent orchestration layer with tool use, longterm memory, and dynamic skill activation.

## Architecture

```
┌──────────────────────────────────────────────────┐
│              Agent Orchestration (LangGraph)       │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ Customer     │  │ RxNorm Drug  │  │ Security │ │
│  │ Support Agent│  │ Mapping Agent│  │ Agent    │ │
│  │ (voice/email)│  │ (email only) │  │ (email only)   │ │
│  └──────┬───────┘  └──────┬───────┘  └────┬─────┘ │
│         │                 │               |        │
│  ┌──────▼─────────────────▼───────────────▼───┐   │
│  │        AgentFactory (StateGraph builder)    │   │
│  │  ┌─────────┐ ┌─────────┐ ┌──────────────┐  │   │
│  │  │ Routing │ │ Tool    │ │ Dynamic Skill│  │   │
│  │  │ (cond.) │ │ Node    │ │ Activation   │  │   │
│  │  └─────────┘ └─────────┘ └──────────────┘  │   │
│  └─────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
         │              │              │
    ┌────▼────┐   ┌─────▼─────┐  ┌────▼────┐
    │Postgres │   │   Redis   │  │  Milvus │
    │(state + │   │ (session  │  │(RAG/    │
    │ memory) │   │  cache)   │  │ vector) │
    └─────────┘   └───────────┘  └─────────┘
```

## Key Technical Highlights

| Feature | Implementation |
|---------|---------------|
| **Agent Framework** | LangGraph `StateGraph` with conditional routing, tool nodes, and `PostgresStore` for long-term memory |
| **Multi Channel** | Same agent codebase handles voice (ElevenLabs/Twilio) and email (SendGrid) with channel aware routing |
| **Dynamic Skills** | Agents activate/deactivate skills at runtime via `activate_skill` / `deactivate_skill` tools, the LLM decides which skills it needs |
| **Longterm Memory** | `PostgresStore` namespaces store conversation summaries, session outcomes, and cross-session learnings per customer |
| **RAG Pipeline** | Milvus/Zilliz Cloud for RxNorm drug semantic search with hybrid retrieval (semantic + scalar filtering) |
| **Async Email** | RabbitMQ decouples SendGrid webhook from agent processing with retry (3x) and dead letter queue |
| **Healthcare NLP** | Custom skills for clinical entity extraction, text normalization, and RxNorm code mapping |
| **Deployment** | Docker Compose for local dev, ECS Fargate + RDS + ElastiCache + Amazon MQ for production |

## Agent Architecture Deep-Dive

Each agent is a **LangGraph StateGraph** compiled with checkpointing and a shared tool registry:

```json
{
  "name": "customer_support_agent",
  "llm": "kimi-k2.5",
  "tools": ["activate_skill", "retrieve_conversation_history", ...],
  "skill_names": ["appointment_booking_skill", "email_skill"],
  "communication_type": "voice"
}
```

**Graph flow**: `START -> agent (LLM + tool binding) -> conditional route -> tool_node / email_node / END`

The `agent` node dynamically binds active skill tools at each turn, so the LLM only "sees" relevant tools based on the conversation context.

## Skills System

Skills are self-contained modules discovered from `src/skills/*/SKILL.md` with YAML frontmatter:

| Skill | Purpose | Used By |
|-------|---------|---------|
| `appointment_booking_skill` | Book/manage appointments via DB | Customer Support (Voice and Email) |
| `email_skill` | Compose and send emails | Customer Support (Voice) |
| `text_normalize_skill` | Normalize clinical text | RxNorm Agent |
| `clinical_entity_extraction_skill` | Extract drugs/dosages from text | RxNorm Agent |
| `rxnorm_mapping_skill` | Map drug names to RxNorm codes via RAG | RxNorm Agent |

## Quick Start

```bash
cp .env.example .env
# Edit .env with your API keys (OPENAI_API_KEY, TWILIO_*, SENDGRID_*, etc.)

docker compose up

# Seed the database (optional, for demo data)
docker compose exec app python -m app.init_db.seed

# Expose for webhooks (ngrok for local testing)
ngrok http 8000
```

The API runs on `http://localhost:8000` with auto-generated docs at `/docs`.

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/elevenlabs/customer/{phone}` | Customer lookup by phone |
| `POST` | `/api/elevenlabs/agent/run` | Run agent (voice call turn) |
| `POST` | `/api/elevenlabs/agent/end` | End call, persist history |
| `POST` | `/api/sendgrid/inbound` | Receive inbound emails |
| `GET` | `/api/health` | Health check |

## Tech Stack

**Backend**: Python 3.12+, FastAPI, asyncpg, LangGraph, LangChain  
**AI/LLM**: OpenAI-compatible APIs, LangGraph tool-use, dynamic skill activation  
**Voice**: ElevenLabs Conversational AI, Twilio  
**Email**: SendGrid Inbound Parse + outbound, RabbitMQ async processing  
**Data**: PostgreSQL (state + memory), Redis (session), Milvus/Zilliz (RAG)  
**Infra**: Docker Compose, ECS Fargate, GitHub Actions CI/CD  

## Project Structure

```
app/
├── controllers/           # FastAPI routes (ElevenLabs, SendGrid webhooks)
├── src/
│   ├── agents/            # Agent configs, state classes, system prompts
│   │   ├── agent_factory.py   # LangGraph StateGraph builder
│   │   ├── shared_tools/      # Memory, skill activation tools
│   │   ├── customer_support_agent/
│   │   ├── rxnorm_mapping_agent/
│   │   └── security_agent/
│   ├── skills/            # Dynamic skill modules (SKILL.md + tools.py)
│   ├── services/          # Dispatch, registry, RAG, RabbitMQ
│   ├── infrastructure/    # DB, Redis, Milvus clients
│   ├── core/              # Config, state models, agent base class
│   └── utils/             # SendGrid email, validators, logging
├── DAL/                   # Data access layer (CustomerDA)
├── init_db/               # Schema + seed scripts
├── agent_configs.json     # Declarative agent definitions
└── main.py                # FastAPI app with lifespan
```

## Testing

```bash
pytest app/tests/unit/          # Unit tests
pytest app/tests/integration/   # Integration tests (requires Docker)
pytest app/tests/evaluation/    # Evaluation suite
```

## What I Learned

- **LangGraph checkpointing** with `AsyncPostgresSaver` enables true multi-turn conversations across voice calls, but requires careful thread_id management (agent:customer:session format)
- **Dynamic skill activation** (vs. static tool binding) gives the LLM agency to decide what capabilities it needs mid-conversation, reducing prompt bloat
- **RabbitMQ decoupling** for email processing prevents webhook timeouts and enables retry/DLQ patterns that SendGrid Inbound Parse expects
- **Channel-aware routing** in the graph (`voice -> END`, `email -> email_node`) keeps the same agent logic clean across communication channels

## Docs

- [Documentation map](docs/documents.md)
- [Getting started](docs/getting_started.md)
- [Architecture](docs/architecture.md)
- [API](docs/api.md)
- [Database](docs/database.md)
- [RAG](docs/RAG.md)
- [Deployment (AWS)](docs/deploy.md)

## License

MIT
