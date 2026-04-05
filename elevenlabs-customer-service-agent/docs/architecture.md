# Architecture: Customer Service Agent (Tool API with RAG)

## Overview

This system is a **voice AI customer service backend** that exposes HTTP tools for ElevenLabs/Twilio integration. It combines traditional CRUD operations with **RAG (Retrieval-Augmented Generation)** for intelligent document-based responses.

**Key Capabilities:**
- Handle voice call tool requests from ElevenLabs
- Customer profiles and **appointment scheduling** data in PostgreSQL (providers, slots, resource bookings)
- Active call state caching (Redis)
- Document-based Q&A via RAG (MinIO + Milvus)
- Async tool handling for long operations

---

## Current Architecture (Phase 1: 100 calls/day)

```
┌─────────────────────────────────────────────────────────────────┐
│                     ElevenLabs / Twilio                         │
│              (Voice AI platforms - webhook callers)             │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS
                            ▼
┌────────────────────────────────────────────────────────────────┐
│                    Single API Server                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              FastAPI Application                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │ API Routes  │  │   Tools     │  │  RAG Handler    │  │   │
│  │  │ - /health   │  │ - Customer  │  │ - Query Milvus  │  │   │
│  │  │ - /tools/run│  │ - Support   │  │ - Context build │  │   │
│  │  │             │  │ - Handoff   │  │ - Response      │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                   │
│  ┌─────────────────────────┼─────────────────────────────────┐ │
│  │         Data Layer      │                                 │ │
│  │  ┌──────────┐  ┌───────┴──┐  ┌──────────┐  ┌──────────┐   │ │
│  │  │PostgreSQL│  │  Redis   │  │  Milvus  │  │  MinIO   │   │ │
│  │  │(Primary) │  │(Session  │  │(Vector   │  │(Documents│   │ │
│  │  │-customers│  │  Cache)  │  │ Database)│  │  Store)  │   │ │
│  │  │-providers│  │-active   │  │-chunks   │  │-PDFs     │   │ │
│  │  │-appts + │  │ callers  │  │-embeds   │  │-Word     │   │ │
│  │  │ bookings│  │-temp     │  │          │  │-Text     │   │ │
│  │  │-logs     │  │ state    │  │          │  │          │   │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │ │
│  └───────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. API Layer (`app/api/`)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/health` | Health check for monitoring |
| `POST /api/tools/run` | Execute tools by name with context |
| `POST /api/rag/query` | RAG-based document Q&A |

**Request Flow:**
```
ElevenLabs → POST /api/tools/run
    {
      "tool_name": "lookup_customer",
      "parameters": {"phone": "+15551234567"},
      "call_sid": "CA123",
      "from_number": "+15551234567"
    }
                 ↓
         ┌───────────────┐
         │ Build Context │ → CallContext (call_sid, phone, etc.)
         └───────────────┘
                 ↓
         ┌───────────────┐
         │Tool Dispatcher│ → registry.run(tool_name, args, context)
         └───────────────┘
                 ↓
         ┌───────────────┐
         │ Return Result │ → {"result": "...", "is_error": false}
         └───────────────┘
```

### 2. Database Layer

#### PostgreSQL (Primary Data Store)

**Tables:**
- `customers` - Caller profiles, contact info
- `providers` - Bookable resources (doctors, nurses, rooms, equipment)
- `slot_templates` - 30-minute start times (lunch hour omitted from templates)
- `appointments` - Booked visits (`scheduled_at`, status, notes)
- `appointment_resource_bookings` - Per-resource slot reservations (created on confirm; unique per provider/date/slot prevents double booking)
- `callback_requests` - Scheduled callbacks
- `tool_logs` - JSONB logs of all tool executions
- `documents` - Metadata linking to MinIO files

**Why PostgreSQL:**
- ACID compliance for transactions
- JSONB for flexible logs
- Full-text search (backup for RAG)
- Mature, well-understood

#### Redis (Session Cache)

**Cache Pattern:**
```
Call Starts:
  PostgreSQL ──▶ Redis (active:call_sid)
                      ├─ customer info
                      ├─ customer / appointment context
                      ├─ conversation state
                      └─ TTL: 1 hour

During Call:
  All reads from Redis (sub-millisecond)

Call Ends:
  Redis ──▶ Update PostgreSQL (if changes)
         ──▶ DEL active:call_sid
```

**Why Redis:**
- Fast lookups during voice conversation
- Reduces PostgreSQL load
- Handles temporary conversation state

#### Milvus (Vector Database)

**RAG Pipeline:**
```
Document Upload:
  Employee → MinIO (store PDF/Word)
         → Text Extraction
         → Chunk into segments
         → Generate embeddings (OpenAI/Local model)
         → Store in Milvus (vector + metadata)

Query Flow:
  Caller asks question
         → Convert to embedding
         → Milvus similarity search (top_k=5)
         → Retrieve relevant chunks
         → Build context for AI response
         → Return natural language answer
```

**Why Milvus:**
- Optimized for high-dimensional vector search
- Handles millions of document chunks
- Sub-second semantic search

#### MinIO (Object Storage)
**reason:**
- Allow user to store unstructured daeta (images, videos, logs, etc..)
- S3 compatibility: Use amazon S3 REST API, allowing applications written for AWS to run seamlessly on MinIO
- High Perfomance
- Deplyment Flexibility: Bare metal, public cloud, kubernetes environments
- Enterprise-Grade Security
- Scalability & Resilience

**Storage:**
- Raw documents (PDF, Word, Excel, TXT)
- Extracted text files (for backup)
- Call recordings (if enabled in future)
- Exported reports

**Why MinIO:**
- S3-compatible API
- Self-hosted (data control)
- Cost-effective for files

---

## Tool Registry System

```python
# Tool Registration Pattern
@app.tools.registry.register("lookup_customer")
async def lookup_customer(arguments: dict, context: CallContext) -> str:
    # 1. Check Redis cache first
    cached = await redis.get(f"customer:{context.from_number}")
    if cached:
        return cached
    
    # 2. Query PostgreSQL
    customer = await db.fetchrow(
        "SELECT * FROM customers WHERE phone = $1",
        context.from_number
    )
    
    # 3. Cache in Redis
    await redis.setex(f"customer:{context.from_number}", 300, json.dumps(customer))
    
    return format_customer_response(customer)
```

**Available Tools:**

| Category | Tools |
|----------|-------|
| **Customer** | `lookup_customer`, `get_account_info` |
| **Support** | `create_ticket`, `check_refund_eligibility`, `request_refund` (stubs; no backing tables in current schema) |
| **Scheduling** | `create_appointment` (writes `appointments`; resource bookings and availability search to be wired in app code) |
| **Handoff** | `transfer_to_agent`, `schedule_callback` |
| **RAG** | `query_knowledge_base` |

---

## RAG (Retrieval-Augmented Generation) Flow

### Document Ingestion
```
Employee Upload
      │
      ▼
┌─────────────┐
│   MinIO     │ ── Store raw file
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Extract   │ ── Text extraction (PDF miner, docx2txt)
│   + Chunk   │ ── Split into 500-token chunks with overlap
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Embed      │ ── Generate vector embeddings
│  (OpenAI)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Milvus    │ ── Store (vector + text + metadata)
└─────────────┘
```

### Query Flow
```
Caller: "What's the return policy?"
              │
              ▼
    ┌─────────────────┐
    │  ElevenLabs AI  │ ── Detects knowledge need
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ POST /rag/query │ ── Send to backend
    │ { "query": "..."}│
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  Embed Query    │ ── Same embedding model
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  Milvus Search  │ ── Similarity search
    │  (top_k=5)      │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  Build Context  │ ── Combine chunks
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Return Response │ ── Natural language answer
    └─────────────────┘
```

---

## Handling Long Operations (30+ seconds)

**Problem:** Some tools (e.g. heavy integrations, batch eligibility checks) take >30s
**Solution:** Async pattern with ElevenLabs conversation management

```
Scenario: A long-running tool job (e.g. external scheduling API) takes 2 minutes

ElevenLabs                    Our API
──────────                    ───────
   │                             │
   │──POST /tools/run───────────▶│
   │  {tool: "slow_operation"}  │
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
- For Phase 1: Use Celery + Redis as message broker
- At 100 calls/day: Can use simple background threads
- PostgreSQL table: `async_jobs` to track job status

---

## Security & Access Control

### Document Security (RAG)
```sql
-- documents table with access control
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    company_id UUID REFERENCES companies(id),
    minio_path VARCHAR(500),
    milvus_id VARCHAR(100),
    access_level VARCHAR(50), -- 'public', 'agents_only', 'admin_only'
    uploaded_by UUID,
    created_at TIMESTAMPTZ
);

-- RAG query only searches docs where company_id matches caller's company
```

### Authentication
- **No user authentication** (internal ElevenLabs webhooks)
- **API key validation** for employee document upload endpoints
- **Rate limiting** to prevent abuse

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
| Error rate | Application | > 1% |

**Logging Strategy:**
- Application logs → CloudWatch
- Tool execution logs → PostgreSQL JSONB
- Access logs → S3 (via ALB when added)

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
         ┌────────┐  ┌────────┐
         │ MinIO  │  │ Message│
         │Cluster │  │ Queue  │
         │        │  │(Celery)│
         └────────┘  └────────┘
              │
              ▼
         ┌────────┐
         │Background│
         │Workers  │
         └────────┘
```

**Additions:**
- Load balancer for high availability
- Redis Sentinel for HA
- PostgreSQL read replica
- Message queue (Celery + Redis/SQS)
- Background worker processes

---

## Folder Structure

```
app/
├── api/
│   ├── routes.py           # HTTP endpoints
│   └── middleware.py       # Logging, request ID
├── services/
│   ├── tool_dispatcher.py  # Tool execution orchestrator
│   ├── rag_service.py      # RAG query handler
│   └── job_queue.py        # Async job management
├── tools/
│   ├── registry.py         # Tool registration system
│   ├── customer_tools.py   # Customer lookup tools
│   ├── support_tools.py    # Support stubs (tickets/refunds)
│   ├── handoff_tools.py    # Transfer/callback tools
│   └── rag_tools.py        # Knowledge base query
├── models/
│   ├── conversation.py     # CallContext
│   ├── customer.py         # Pydantic models
│   └── document.py         # Document metadata
├── infrastructure/
│   ├── database.py         # PostgreSQL pool
│   ├── redis.py            # Redis client
│   ├── milvus.py           # Vector DB client
│   └── minio.py            # Object storage client
├── rag/
│   ├── document_processor.py # Text extraction, chunking
│   ├── embedding.py        # Vector generation
│   └── retriever.py          # Milvus query builder
└── main.py                 # FastAPI app factory
```

---

## Environment Variables

```bash
# PostgreSQL
DATABASE_URL=postgresql://user:pass@localhost:5432/customer_service

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=optional

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION=document_chunks

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=documents

# Embeddings
OPENAI_API_KEY=sk-...  # or local model endpoint
EMBEDDING_MODEL=text-embedding-ada-002

# App
LOG_LEVEL=INFO
ENVIRONMENT=development
TOOL_TIMEOUT_SECONDS=30
```

---

## Summary

This architecture supports:
- **100 calls/day** (current) with single server
- **RAG-powered** responses from company documents
- **Sub-second** customer lookups via Redis cache
- **Async handling** for long-running operations
- **Clear upgrade path** to distributed architecture

**Key Decisions:**
- ✅ PostgreSQL: Single source of truth
- ✅ Redis: Active call state only (not persistent data)
- ✅ Milvus: Required for RAG vector search
- ✅ MinIO: Document storage with extraction pipeline
- ✅ No MongoDB: Logs in PostgreSQL JSONB
- ✅ No load balancer yet: Add when scaling

**Next Steps:**
1. Implement document ingestion pipeline
2. Build RAG query endpoint
3. Add Redis caching to customer tools
4. Set up monitoring (CloudWatch/Datadog)
5. Test async tool pattern with ElevenLabs
