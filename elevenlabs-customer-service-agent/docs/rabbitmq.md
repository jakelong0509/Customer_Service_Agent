# RabbitMQ: Message Broker for Customer Service Agent

## What is RabbitMQ?

RabbitMQ is an open-source **message broker** that implements the **AMQP** (Advanced Message Queuing Protocol) standard. It acts as middleware between producers (applications that send messages) and consumers (applications that process messages), enabling **asynchronous, decoupled communication** between system components.

At its core, RabbitMQ is a **post office for software**: it accepts messages from producers, routes them through exchanges to queues, and delivers them to consumers. It does **not** execute business logic. It only ensures reliable message delivery.

### Core Concepts

```
┌──────────┐     ┌─────────────┐     ┌───────────┐     ┌──────────┐
│ Producer  │────▶│   Exchange  │────▶│   Queue   │────▶│ Consumer │
│ (FastAPI) │     │ (Router)    │     │ (Buffer)  │     │ (Worker) │
└──────────┘     └─────────────┘     └───────────┘     └──────────┘
                        │
                        │ Binding rules
                        ▼
                 ┌─────────────┐
                 │   Queue 2   │────▶ Consumer 2
                 └─────────────┘
```

| Concept | Description |
|---------|-------------|
| **Producer** | Application that sends messages (e.g., FastAPI endpoint) |
| **Exchange** | Receives messages from producers and routes them to queues based on rules |
| **Queue** | Buffer that stores messages until a consumer processes them |
| **Consumer** | Application that receives and processes messages (e.g., worker process) |
| **Binding** | Rule that links an exchange to a queue |
| **Routing Key** | Address the exchange uses to route messages to the correct queue |
| **ACK** | Confirmation from consumer that a message was processed successfully |
| **NACK** | Signal from consumer that processing failed; message can be re-queued |
| **Connection** | TCP connection between application and RabbitMQ |
| **Channel** | Virtual connection inside a TCP connection (multiplexing) |

### Exchange Types

| Type | Routing Behavior | Use Case |
|------|-----------------|----------|
| **Direct** | Routes to queue where routing key exactly matches binding key | Point-to-point (specific agent task) |
| **Fanout** | Broadcasts to **all** bound queues, ignoring routing key | Event broadcasting (e.g., "email received") |
| **Topic** | Routes using wildcard patterns (`*` = one word, `#` = zero or more) | Multi-topic routing (`email.inbound.*`) |
| **Headers** | Routes based on message header attributes instead of routing key | Complex routing by metadata |

---

## What Problem Does RabbitMQ Solve?

### The Problem: Synchronous Heavy Work in HTTP Handlers

Without a message broker, the Customer Service Agent processes inbound emails directly inside FastAPI's request lifecycle (via `BackgroundTasks`):

```
Current Flow:
SendGrid Webhook → POST /api/sendgrid/inbound
    → FastAPI BackgroundTasks → invoke_agent() → Agent processes email
    → Returns HTTP 200 (but agent work still runs in the same process)
```

This creates several problems:

| Problem | Impact |
|---------|--------|
| **No durability** | If the API process restarts (deploy, crash), in-flight `BackgroundTasks` are **lost**: emails go unanswered |
| **No backpressure** | A burst of inbound emails piles unbounded work into one API process, exhausting memory/CPU |
| **No horizontal scaling** | Multiple API replicas each run their own in-process tasks: no shared work queue, no coordinated concurrency |
| **No retry / DLQ** | If `invoke_agent()` raises, the email is silently dropped: no retry, no dead-letter queue for manual inspection |
| **Coupled lifecycle** | API deployment kills in-flight work; scaling API replicas does not scale worker capacity independently |

### The Solution: Decouple with RabbitMQ

RabbitMQ solves all of these by inserting a **durable queue** between the HTTP layer and the worker layer:

```
With RabbitMQ:
SendGrid Webhook → POST /api/sendgrid/inbound
    → Publish message to RabbitMQ queue
    → Returns HTTP 200 immediately (fast, reliable)

RabbitMQ Queue → Worker process (separate from API)
    → invoke_agent() → Agent processes email
    → ACK message on success / NACK + retry on failure
```

### Benefits Summary

| Benefit | How RabbitMQ Helps |
|---------|--------------------|
| **Durability** | Messages persist to disk; survive process restarts and deploys |
| **Backpressure** | Bursts queue up instead of overwhelming the API; workers consume at their own pace |
| **Horizontal scaling** | Multiple API replicas publish to the same queues; multiple workers consume concurrently |
| **Retries & DLQ** | Failed messages can be re-queued with delay, or routed to a dead-letter queue for inspection |
| **Decoupled lifecycle** | Deploy the API without killing in-flight work; scale workers independently of API replicas |
| **Observability** | Queue depth, consumer lag, and message rates are visible in the RabbitMQ Management UI |
| **Guaranteed delivery** | Messages are only removed from the queue after the consumer ACKs: no silent drops |

### When RabbitMQ is Overkill

For low-volume development (< 100 calls/day), FastAPI `BackgroundTasks` is simpler and sufficient. RabbitMQ becomes valuable when you need:

- Multiple API replicas behind a load balancer
- Guaranteed delivery (no lost emails on deploy/crash)
- Independent scaling of workers vs API
- Retry logic with dead-letter queues
- Observable queue depth for operational monitoring

---

## Installing RabbitMQ

### Option 1: Docker (Recommended for Development)

```bash
docker run -d --hostname my-rabbit --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  rabbitmq:3-management
```

- **Port 5672**: AMQP protocol (application connections)
- **Port 15672**: Management UI (http://localhost:15672, login: `guest` / `guest`)

Verify it's running:

```bash
docker ps | grep rabbitmq
curl http://localhost:15672  # Should return the management UI
```

**Troubleshooting:** If you see `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`, Docker Desktop is **not running**. Launch it from the Windows Start menu, wait ~60 seconds, then retry. If Docker Desktop is not installed, download it from https://www.docker.com/products/docker-desktop/

### Option 2: Native Installation (Ubuntu / WSL)

If you don't have Docker, install RabbitMQ natively in WSL:

```bash
# Update packages
sudo apt-get update

# Install RabbitMQ
sudo apt-get install rabbitmq-server -y

# Start the service
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server

# Enable the management plugin (web UI)
sudo rabbitmq-plugins enable rabbitmq_management

# Verify
sudo rabbitmqctl status
```

Management UI: http://localhost:15672 (default: `guest` / `guest`)

### Option 3: Add to Docker Compose (Project Integration)

Add to your existing `docker-compose.yml`:

```yaml
services:
  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "-q", "ping"]
      interval: 10s
      timeout: 10s
      retries: 5

  app:
    # ... existing config ...
    depends_on:
      rabbitmq:
        condition: service_healthy
    environment:
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/

volumes:
  rabbitmq_data:
```

### Option 4: AWS: Amazon MQ (Managed RabbitMQ)

For production on AWS, use **Amazon MQ** (managed ActiveMQ/RabbitMQ):

1. Go to **Amazon MQ → Brokers → Create broker**
2. Engine: **RabbitMQ**
3. Instance type: single-instance (dev) or cluster (production)
4. VPC / security group: same as your ECS tasks
5. Note the **AMQP endpoint** (e.g., `amqps://user:pass@b-xxx.mq.us-east-1.amazonaws.com:5671`)
6. Set `RABBITMQ_URL` in your ECS task definition

---

## How RabbitMQ is Used in This Project

### Architecture Overview

The project uses RabbitMQ to decouple **inbound email processing** from the HTTP layer. The FastAPI endpoint publishes a message to a queue; a separate worker process consumes the message and runs the agent.

```
┌────────────────────────────┐     ┌──────────────────────────────┐
│  ElevenLabs / Twilio       │     │  SendGrid Inbound Parse      │
│  (voice webhooks)          │     │  POST /api/sendgrid/inbound  │
└─────────────┬──────────────┘     └──────────────┬───────────────┘
              │ HTTPS                            │ HTTPS
              └──────────────────┬───────────────┘
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│  FastAPI - app/main.py                                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  POST /api/sendgrid/inbound                              │  │
│  │    → Validates request                                   │  │
│  │    → Builds message payload                              │  │
│  │    → Publishes to RabbitMQ queue                         │  │
│  │    → Returns HTTP 200 immediately                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
              │
              │ Publish
              ▼
┌────────────────────────────────────────────────────────────────┐
│  RabbitMQ                                                      │
│  ┌──────────────────────┐  ┌──────────────────────┐           │
│  │ email_inbound_queue  │  │  DLQ (dead-letter)   │           │
│  │ (durable, persisted) │  │  (failed messages)   │           │
│  └──────────┬───────────┘  └──────────────────────┘           │
└─────────────┼──────────────────────────────────────────────────┘
              │ Consume
              ▼
┌────────────────────────────────────────────────────────────────┐
│  Worker Process (separate from uvicorn)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. Receive message from queue                           │  │
│  │  2. Parse agent_name, request, customer info             │  │
│  │  3. invoke_agent(agent_name, request, customer, sid)     │  │
│  │  4. Send reply email via SendGrid (if email agent)       │  │
│  │  5. ACK message on success                               │  │
│  │  6. NACK + re-queue on failure (up to N retries)         │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

### Queue Design

| Queue Name | Purpose | Durability | Consumers |
|------------|---------|------------|-----------|
| `email_inbound_queue` | Inbound email processing tasks | Durable, persisted | Email worker(s) |
| `email_inbound_dlq` | Failed messages after max retries | Durable | Manual inspection / alerting |

### Message Format

Messages published to `email_inbound_queue` use JSON:

```json
{
  "agent_name": "rxnorm_mapping_agent_email",
  "request": "Email Conversation ---\n        Title: RxNorm Question\n        From: customer@example.com\n        To: rxnorm@clinic.com\n        Body: What is the generic for Lipitor?\n        Message-ID: <abc123@mail.com>\n        ",
  "message_id": "<abc123@mail.com>",
  "from_email": "customer@example.com",
  "to": "rxnorm@clinic.com",
  "subject": "RxNorm Question",
  "references": ""
}
```

### Important: RabbitMQ Does NOT Send Results to Users

RabbitMQ is a **fire-and-forget message broker**. After the consumer ACKs, RabbitMQ's job is done. It does **not** send results back to the user or the producer.

In this project:
- The **worker** sends the reply email to the customer via the **SendGrid Email API**
- RabbitMQ is only responsible for **reliable delivery** of the task to the worker
- The user receives the result via email, not via RabbitMQ

If you need the result sent back through RabbitMQ (RPC pattern), you would use a **reply queue** with a `correlation_id`. However, this is **not recommended** for this project, as the async email reply pattern is simpler and more appropriate.

---

## Client Library: pika and Connection Types

### Why `pika.BlockingConnection` is "Blocking"

`BlockingConnection` means **each operation waits (blocks) until it completes** before moving to the next line of code. It is **synchronous**: the thread stops and waits.

```python
connection = pika.BlockingConnection(...)  # Blocks until TCP connected
channel = connection.channel()             # Blocks until channel created
channel.queue_declare(queue='my_queue')    # Blocks until queue declared
channel.basic_publish(...)                 # Blocks until message sent
channel.start_consuming()                  # Blocks FOREVER - sits here listening
```

```
Timeline:
──▶ connect() ──── wait ──── connected ─▶
──▶ channel()  ──── wait ──── created  ─▶
──▶ publish()  ──── wait ──── sent     ─▶
──▶ consume()  ──── wait forever...
```

### Connection Types Comparison

| Connection Type | Model | Blocks Thread? | Best For |
|----------------|-------|----------------|----------|
| `BlockingConnection` | Synchronous | Yes: each call waits | **Worker processes** (dedicated consumers) |
| `SelectConnection` | Event loop (async, no asyncio) | No | Single-threaded async without asyncio |
| `AsyncioConnection` | Async with `asyncio` | No | **FastAPI / async applications** |

### When to Use Each

**Worker process**: use `BlockingConnection`. The worker is a dedicated process whose only job is to consume messages. Blocking is natural and simple here.

**FastAPI endpoint**: use `aio_pika` (async). If you use `BlockingConnection` inside FastAPI, it **freezes the entire event loop**: all other HTTP requests hang while waiting for RabbitMQ to respond:

```python
# BAD - blocks FastAPI's event loop
@app.post("/api/sendgrid/inbound")
async def sendgrid_inbound(...):
    connection = pika.BlockingConnection(...)  # FREEZES ALL REQUESTS
    channel = connection.channel()
    channel.basic_publish(...)

# GOOD - async, does not block the event loop
import aio_pika

@app.post("/api/sendgrid/inbound")
async def sendgrid_inbound(...):
    connection = await aio_pika.connect_robust("amqp://localhost")
    async with connection:
        channel = await connection.channel()
        await channel.default_exchange.publish(
            aio_pika.Message(body=json.dumps(payload).encode()),
            routing_key="email_inbound_queue",
        )
```

| Scenario | Use | Reason |
|----------|-----|--------|
| **Worker process** (standalone `python worker.py`) | `pika.BlockingConnection` | Worker's only job is consuming: blocking is natural |
| **FastAPI endpoint** (publishing to queue) | `aio_pika` (async) | Must not block the async event loop |
| **Non-async Python app** (Flask, scripts) | `pika.BlockingConnection` | No event loop to block |

---

## Publisher Side (FastAPI Endpoint)

The `POST /api/sendgrid/inbound` endpoint in `app/controllers/sendgrid.py` publishes a message to RabbitMQ instead of using `BackgroundTasks`:

```python
# Before (BackgroundTasks):
background_tasks.add_task(
    _run_inbound_agent,
    agent_request.agent_name,
    agent_request,
    customer,
    session_id,
)

# After (RabbitMQ with aio_pika - async, non-blocking):
import aio_pika, json

async def publish_to_queue(agent_request: SendGridInboundRequest):
    connection = await aio_pika.connect_robust(
        os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    )
    async with connection:
        channel = await connection.channel()
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(agent_request.dict()).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key="email_inbound_queue",
        )
```

The endpoint still returns `HTTP 200` immediately, and SendGrid gets a fast acknowledgment.

---

## Consumer Side (Worker Process)

### How the Worker Runs

You do **not** write a `while True` loop yourself. Pika's `channel.start_consuming()` **is** the infinite loop. It runs forever internally, waiting for messages and calling your callback each time one arrives.

```python
# What pika does internally (simplified):
def start_consuming():
    while True:                           # Infinite loop
        message = wait_for_message()      # Block until a message arrives
        callback(channel, method, properties, message)  # Call YOUR function
```

```
start_consuming()
  │
  ├──▶ waiting for message... (idle, no CPU)
  │
  ├──▶ message arrives! → callback() → your code runs → ACK
  │
  ├──▶ waiting for message... (idle again)
  │
  ├──▶ message arrives! → callback() → your code runs → ACK
  │
  ├──▶ waiting for message...
  │
  └──▶ (runs forever until Ctrl+C or the process is killed)
```

### Full Worker Implementation

```python
# worker.py
import pika
import json
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from src.services.dispatch_agent import invoke_agent
from src.core.agent_run_request_model import SendGridInboundRequest
from src.infrastructure.database import init_pool, close_pool
from src.infrastructure.redis import init_redis, close_redis
from src.infrastructure.milvus import init_milvus, close_milvus
from src.services.agent_registry import create_agent

MAX_RETRIES = 3

async def process_message(data: dict):
    agent_request = SendGridInboundRequest(**data)
    session_id = agent_request.message_id or ""
    customer = None
    result = await invoke_agent(
        agent_request.agent_name,
        agent_request,
        customer,
        session_id,
    )
    return result

def callback(ch, method, properties, body):
    data = json.loads(body)
    retry_count = 0
    if properties.headers and 'x-retry-count' in properties.headers:
        retry_count = int(properties.headers['x-retry-count'])

    try:
        print(f"[Worker] Processing: {data.get('subject', 'no subject')} (attempt {retry_count + 1})")
        result = asyncio.run(process_message(data))
        print(f"[Worker] Done: {result}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"[Worker] Error: {e}")
        if retry_count < MAX_RETRIES:
            ch.basic_publish(
                exchange='',
                routing_key=method.routing_key,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    headers={'x-retry-count': retry_count + 1},
                ),
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print(f"[Worker] Re-queued (attempt {retry_count + 1}/{MAX_RETRIES})")
        else:
            ch.basic_publish(
                exchange='',
                routing_key='email_inbound_dlq',
                body=body,
                properties=pika.BasicProperties(delivery_mode=2),
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print(f"[Worker] Sent to DLQ after {MAX_RETRIES} retries")

async def startup():
    init_milvus()
    await init_pool()
    await init_redis()
    create_agent()

async def shutdown():
    await close_pool()
    await close_redis()
    close_milvus()

if __name__ == '__main__':
    asyncio.run(startup())

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=os.getenv('RABBITMQ_HOST', 'localhost'),
            port=int(os.getenv('RABBITMQ_PORT', '5672')),
            credentials=pika.PlainCredentials(
                os.getenv('RABBITMQ_USER', 'guest'),
                os.getenv('RABBITMQ_PASS', 'guest'),
            ),
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue='email_inbound_queue', durable=True)
    channel.queue_declare(queue='email_inbound_dlq', durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='email_inbound_queue', on_message_callback=callback)

    print("[Worker] Started. Waiting for messages... (Ctrl+C to stop)")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\n[Worker] Stopping...")
        channel.stop_consuming()
        connection.close()
        asyncio.run(shutdown())
```

### Message Lifecycle

```
1. SendGrid sends POST /api/sendgrid/inbound
2. FastAPI validates, builds payload, publishes to email_inbound_queue
3. FastAPI returns HTTP 200 to SendGrid (fast)
4. RabbitMQ stores the message durably on disk
5. Worker receives the message from the queue
6. Worker calls invoke_agent() → agent processes the email
7a. Success → Worker sends ACK → RabbitMQ deletes the message
7b. Failure → Worker sends NACK + re-queue (up to MAX_RETRIES)
7c. Max retries exceeded → Message routed to email_inbound_dlq
8. Agent's reply email is sent to the customer via SendGrid API
```

```
┌───────────┐
│ Published │──▶ Queued ──▶ Delivered ──▶ Processed ──▶ ACKed
│           │                │                         (removed)
│           │                ▼
│           │           ┌─────────┐
│           │           │ Crashed │──▶ Re-queued (retry)
│           │           └────┬────┘
│           │                │ (max retries)
│           │                ▼
│           │           ┌────────────────────┐
│           │           │ Dead Letter Queue  │
│           │           │ (manual inspection)│
│           │           └────────────────────┘
└───────────┘
```

---

## Why the Worker Must Be a Separate Process (NOT Inside FastAPI Lifespan)

It is tempting to put the RabbitMQ consumer inside FastAPI's `lifespan` so everything runs in one process. **This defeats the entire purpose of using RabbitMQ.**

```python
# BAD - do not do this
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_milvus()
    await init_pool()
    await init_redis()
    create_agent()
    thread = threading.Thread(target=run_rabbitmq_consumer, daemon=True)
    thread.start()
    yield
    await close_pool()
    await close_redis()
    close_milvus()
```

### Problem 1: Loss of Independent Scaling

```
SEPARATE PROCESSES (correct):
┌────────┐ ┌────────┐ ┌────────┐     ┌────────┐ ┌────────┐ ┌────────┐
│ API 1  │ │ API 2  │ │ API 3  │     │Worker 1│ │Worker 2│ │Worker 3│
└───┬────┘ └───┬────┘ └───┬────┘     └───┬────┘ └───┬────┘ └───┬────┘
    └──────────┴──────────┘               └──────────┴──────────┘
         Publish (fast)                       Consume (slow)
              │                                    │
              └────────── RabbitMQ ────────────────┘
  Scale API and Workers INDEPENDENTLY

COMBINED (lifespan, wrong):
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ API 1            │  │ API 2            │  │ API 3            │
│ + Worker thread  │  │ + Worker thread  │  │ + Worker thread  │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         └──────────────────────┴──────────────────────┘
                    EVERYTHING tied together
  Can't scale workers without scaling API (and vice versa)
```

| Scenario | Separate Processes | Combined (lifespan) |
|----------|-------------------|---------------------|
| 100 emails queued, 1 API replica | Add 5 workers | Must add 5 API replicas |
| High HTTP traffic, no emails | Scale API only | Workers scale too (wasted) |
| Worker crashes | API stays up, restart worker | API process may go down too |

### Problem 2: Loss of Fault Isolation

```
Separate processes:
  Worker crashes (OOM, agent error)
    → API stays up, keeps accepting requests
    → Messages re-queued by RabbitMQ
    → Restart worker, processing resumes

Combined (lifespan):
  Worker thread crashes
    → Daemon thread? Silently dies, no consumer anymore
    → Non-daemon thread? May crash the entire API process
    → Either way: messages pile up, nobody consuming
```

### Problem 3: Resource Contention

Agent processing is **CPU-heavy and memory-heavy** (LLM calls, RAG, Milvus queries). Running it in the same process as the HTTP API starves HTTP handlers:

```
Same process:
┌──────────────────────────────────────────┐
│  FastAPI (uvicorn)                       │
│  HTTP handler → 50ms                     │
│  Worker thread → 30s (agent processing)  │ ← competes for CPU, memory
│  Worker thread → 30s (agent processing)  │ ← starves HTTP handlers
│  Result: HTTP requests slow down / hang  │
└──────────────────────────────────────────┘

Separate processes:
┌──────────────────┐     ┌──────────────────┐
│  FastAPI          │     │  Worker           │
│  HTTP only        │     │  Agent only       │
│  Fast & light     │     │  Heavy processing │
│  200ms max        │     │  30s is fine      │
└──────────────────┘     └──────────────────┘
```

### Problem 4: Deploy Kills In-Flight Work

```
Combined (lifespan):
  Deploy new API code → uvicorn restarts → worker thread killed → in-flight work LOST

Separate processes:
  Deploy new API code → uvicorn restarts → worker keeps running → zero interrupted jobs
```

### When Is Combining Acceptable?

| Scenario | Combined (lifespan) | Separate Process |
|----------|---------------------|------------------|
| Dev / local testing | Acceptable for simplicity | Better |
| Single replica, < 50 emails/day | Acceptable | Recommended |
| Multiple API replicas | **Do not** | Required |
| Production | **Do not** | Required |
| Agent processing > 5s | **Do not** | Required |

---

## Scaling Workers

### How Multiple Workers Work

5 workers = 5 separate processes, all consuming from the **same queue**. RabbitMQ distributes messages **round-robin** automatically:

```
Message 1 → Worker 1
Message 2 → Worker 2
Message 3 → Worker 3
Message 4 → Worker 4
Message 5 → Worker 5
Message 6 → Worker 1    ← cycles back
```

With `prefetch_count=1`, each worker gets **max 1 un-ACKed message** at a time - fast workers get more messages, slow workers get fewer. **Automatic load balancing.**

### Running Multiple Workers

**Development: Docker Compose:**

```yaml
services:
  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_HOST=redis
    depends_on:
      - rabbitmq
    deploy:
      replicas: 5    # ← change this number to scale
    restart: unless-stopped
```

```bash
docker-compose up -d worker                    # starts 5 workers
docker-compose up -d --scale worker=10         # scale to 10
docker-compose up -d --scale worker=2          # scale down to 2
```

**Production: ECS Fargate** (matches `docs/deploy.md`):

```bash
aws ecs update-service \
  --cluster customer-service-cluster \
  --service customer-service-worker \
  --desired-count 5
```

**Production: Kubernetes:**

```bash
kubectl scale deployment csa-worker --replicas=10
```

**Simple Linux server: systemd template:**

```ini
# /etc/systemd/system/csa-worker@.service
[Unit]
Description=CSA Worker %i
After=network.target rabbitmq.service

[Service]
Type=simple
ExecStart=/opt/app/.venv/bin/python worker.py
Restart=always
RestartSec=5
Environment=WORKER_ID=%i

[Install]
WantedBy=multi-user.target
```

```bash
for i in $(seq 1 5); do sudo systemctl start csa-worker@$i; done
```

### Auto-Scaling Based on Queue Depth

Workers don't replicate themselves - the **orchestrator** monitors the queue and spawns/removes workers automatically:

```
Queue depth: 3    → 1 worker  (enough)
Queue depth: 50   → 3 workers (auto-scale up)
Queue depth: 200  → 8 workers (auto-scale up)
Queue depth: 0    → 2 workers (auto-scale down to minimum)
```

**ECS Fargate + CloudWatch alarm:**

1. Publish queue depth to CloudWatch every 60 seconds (sidecar script)
2. Create alarm when queue depth > 20
3. Configure ECS target tracking scaling policy:

```bash
aws ecs register-scalable-target \
  --service-namespace ecs \
  --resource-id service/customer-service-cluster/customer-service-worker \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 1 \
  --max-capacity 10
```

**Kubernetes + KEDA** (best-in-class, native RabbitMQ trigger):

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: csa-worker-scaler
spec:
  scaleTargetRef:
    name: csa-worker
  minReplicaCount: 0          # Scale to zero when idle
  maxReplicaCount: 15
  cooldownPeriod: 300
  triggers:
    - type: rabbitmq
      metadata:
        queueName: email_inbound_queue
        queueLength: "20"
        host: amqp://guest:guest@rabbitmq:5672/
```

| Platform | Auto-Scaling Method | Scale to Zero? | Complexity |
|----------|-------------------|----------------|------------|
| Docker Compose | Manual `--scale` | No | Low |
| ECS Fargate | CloudWatch alarm + scaling policy | No (min 1) | Medium |
| Kubernetes HPA | Custom metrics + HPA | No (min 1) | Medium |
| Kubernetes KEDA | Native RabbitMQ trigger | **Yes** | Low |
| systemd | Manual | No | Low |

### Recommended Approach for This Project

Based on `docs/deploy.md` (ECS Fargate on AWS):

```
Short-term (dev):     Docker Compose, manual --scale
Medium-term (prod):   ECS Fargate + CloudWatch queue depth alarm + auto-scaling
Best-in-class:        Kubernetes + KEDA (if you migrate to K8s later)
```

---

## Environment Variables

Add to `.env`:

```bash
# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASS=guest
RABBITMQ_EMAIL_QUEUE=email_inbound_queue
RABBITMQ_DLQ=email_inbound_dlq
RABBITMQ_MAX_RETRIES=3
```

For production (Amazon MQ):

```bash
RABBITMQ_URL=amqps://user:password@b-xxx.mq.us-east-1.amazonaws.com:5671/
```

---

## Running Locally

### 1. Start RabbitMQ

```bash
# Docker
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management

# Or native (WSL)
sudo systemctl start rabbitmq-server

# Or with docker-compose
docker-compose up -d rabbitmq
```

### 2. Start the FastAPI application

```bash
# Terminal 1
cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Start the worker

```bash
# Terminal 2 (separate from FastAPI)
python worker.py
```

### 4. Verify

- **Management UI**: http://localhost:15672 (`guest` / `guest`)
- **Queue status**: Check the "Queues" tab in the Management UI
- **Test**: Send a test inbound email via SendGrid or curl to `/api/sendgrid/inbound`

```
Terminal 1 (FastAPI)          Terminal 2 (Worker)           RabbitMQ
                              │                             │
uvicorn main:app              python worker.py              │
    │                             │                         │
    │  POST /sendgrid/inbound     │                         │
    │  ──── publish to queue ──────────────────────────────▶│
    │  ◀─── 200 OK (instant)     │                         │
    │                             │◀── deliver message ─────│
    │                             │─── invoke_agent()        │
    │                             │─── send reply email      │
    │                             │─── ACK ─────────────────▶│
    │                             │                         │
    │                             ... runs forever ...       │
```

---

## Common Operations

| Command | Purpose |
|---------|---------|
| `sudo rabbitmqctl status` | Check broker status |
| `sudo rabbitmqctl list_queues` | List all queues and message counts |
| `sudo rabbitmqctl list_queues name messages consumers` | Show queue name, depth, active consumers |
| `sudo rabbitmqctl purge_queue email_inbound_queue` | Remove all messages from a queue |
| `sudo rabbitmqctl list_users` | List all users |
| `sudo rabbitmqctl add_user myuser mypass` | Create a new user |
| `sudo rabbitmqctl set_user_tags myuser administrator` | Grant admin role |
| `sudo rabbitmqctl set_permissions -p / myuser ".*" ".*" ".*"` | Grant permissions |
| `docker logs rabbitmq` | View RabbitMQ logs (Docker) |
| `rabbitmq-diagnostics -q ping` | Health check |

---

## Production Considerations

### Reliability

- Enable **durable queues** and **persistent messages** (`delivery_mode=2`)
- Use **publisher confirms** to ensure messages are accepted by RabbitMQ
- Configure **dead-letter exchanges** for failed messages
- Set up **RabbitMQ clustering** or use **Amazon MQ** for high availability

### Monitoring

| Metric | Alert Threshold |
|--------|----------------|
| Queue depth | Sustained growth (consumers can't keep up) |
| Consumer count | Drops to zero (workers down) |
| Message publish rate | Sudden spike (potential abuse) |
| Unacked message count | Growing (slow or stuck consumers) |
| Memory usage | > 80% of RabbitMQ memory watermark |

### Security

- Use **TLS** for connections in production (`amqps://`)
- Replace default `guest` / `guest` credentials
- Restrict Management UI access to internal networks
- Use **vhosts** to isolate environments (dev, staging, prod)

---

## Client Library Options

| Library | Type | Notes |
|---------|------|-------|
| **pika** | Synchronous | Simple, well-documented; good for workers |
| **aio-pika** | Async (asyncio) | For async FastAPI publishers; native await support |
| **Celery** | Task queue framework | Built on top of RabbitMQ; handles retries, scheduling, monitoring |
| **Kombu** | Messaging library | Underlying library for Celery; can be used standalone |

For this project, **pika** is recommended for the worker process and **aio-pika** for the FastAPI publisher (to avoid blocking the async event loop).

---

## References

- [RabbitMQ Official Documentation](https://www.rabbitmq.com/documentation.html)
- [AMQP 0-9-1 Protocol](https://www.rabbitmq.com/amqp-0-9-1-reference.html)
- [RabbitMQ Tutorials](https://www.rabbitmq.com/getstarted.html)
- [pika Library](https://pika.readthedocs.io/)
- [aio-pika Library](https://aio-pika.readthedocs.io/)
- [KEDA - Kubernetes Event-Driven Auto-Scaling](https://keda.sh/)
- Project architecture: `docs/architecture.md`
- SendGrid controller: `app/controllers/sendgrid.py`
- Agent dispatch: `app/src/services/dispatch_agent.py`
