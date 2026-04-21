## Deploying to AWS: ECS Fargate + RDS + ElastiCache + Amazon MQ

This document explains the AWS services used and walks through a minimal, opinionated setup to deploy the Customer Service Agent — which consists of **two containers** (the FastAPI app and a RabbitMQ worker), plus supporting infrastructure (PostgreSQL, Redis, RabbitMQ, Milvus/Zilliz Cloud).

---

## 1. Architecture overview

```
                    ┌──────────────┐
                    │  ALB (HTTPS) │
                    │  port 443→8000│
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  ECS Service │
                    │  ┌─────────┐ │
                    │  │  app     │ │  FastAPI — handles ElevenLabs & SendGrid webhooks
                    │  │  :8000   │ │
                    │  └─────────┘ │
                    └──────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼───┐ ┌─────▼─────┐ ┌───▼────────┐
       │   RDS    │ │ElastiCache│ │ Amazon MQ  │
       │PostgreSQL│ │  Redis    │ │  RabbitMQ  │
       └──────────┘ └───────────┘ └─────┬──────┘
                                          │
                                   ┌──────▼───────┐
                                   │ ECS Service  │
                                   │ ┌──────────┐ │
                                   │ │  worker   │ │  RabbitMQ consumer (2 replicas)
                                   │ │ (no port) │ │  processes email agent requests
                                   │ └──────────┘ │
                                   └──────────────┘
                                          │
                              ┌───────────┼───────────┐
                              │           │           │
                       ┌──────▼───┐ ┌────▼────┐ ┌────▼─────┐
                       │   RDS    │ │ElastiCh.│ │ Zilliz   │
                       │PostgreSQL│ │  Redis  │ │ Cloud    │
                       └──────────┘ └─────────┘ └──────────┘
```

### Services in this project

| Service | Purpose | AWS managed equivalent |
|---------|---------|----------------------|
| **FastAPI app** | HTTP API for ElevenLabs webhooks, SendGrid inbound parse, health checks | ECS Fargate |
| **RabbitMQ worker** | Async consumer that processes inbound emails via agent dispatch | ECS Fargate |
| **PostgreSQL** | Customer data, conversation history (asyncpg) | RDS PostgreSQL |
| **Redis** | Call session state, caching | ElastiCache for Redis |
| **RabbitMQ** | Message queue decoupling SendGrid webhook from agent processing | Amazon MQ for RabbitMQ |
| **Milvus** | Vector search (drug/RxNorm semantic matching) | Zilliz Cloud (managed, external) |

### Containers

The project has **two Docker images**:

1. **`app`** (`Dockerfile`) — `uvicorn app.main:app --host 0.0.0.0 --port 8000`
   - Endpoints:
     - `GET /api/health` — health check
     - `GET /api/elevenlabs/customer/{phone}` — customer lookup
     - `POST /api/elevenlabs/agent/run` — run agent (voice call)
     - `POST /api/elevenlabs/agent/end` — end call, persist history
     - `POST /api/sendgrid/inbound` — receive inbound emails, publish to RabbitMQ

2. **`rabbitmq-worker`** (`Dockerfile.worker`) — `python rabbitmq_worker.py`
   - Consumes from `sendgrid_email_inbound_queue`
   - Dispatches to the email agent (rxnorm or customer support)
   - Retries up to 3 times, then sends to `email_inbound_dlq`
   - Runs as 2 replicas (configurable)

---

## 2. Prerequisites

- An AWS account with permissions for:
  - ECR, ECS (Fargate), RDS, ElastiCache, Amazon MQ, EC2 (ALB + security groups), ACM, Route 53
- AWS CLI configured locally (optional but helpful)
- Docker installed locally
- This repo checked out and working locally (`docker compose up`)
- A **Zilliz Cloud** account with a serverless cluster (for Milvus vector search)
- External API keys:
  - OpenAI API key
  - ElevenLabs account (configured separately on their dashboard)
  - Twilio account (for phone/webhook integration)
  - SendGrid account (for email inbound parse)
  - LangSmith (optional, for tracing)

Assumed region: **`us-east-1`** (adjust as needed).

---

## 3. Build and push Docker images to ECR

Both `Dockerfile` and `Dockerfile.worker` share the same base (Python 3.12-slim) and `requirements.txt`.

### 3.1 Create ECR repositories

In the AWS Console (or CLI):

```bash
aws ecr create-repository --repository-name customer-service-agent --region us-east-1
aws ecr create-repository --repository-name customer-service-worker --region us-east-1
```

Note the repository URIs:

```
<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/customer-service-agent
<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/customer-service-worker
```

### 3.2 Log in to ECR

```bash
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
```

### 3.3 Build and push both images

From the `elevenlabs-customer-service-agent` directory:

```bash
# App image
docker build -t customer-service-agent .
docker tag customer-service-agent:latest \
  <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/customer-service-agent:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/customer-service-agent:latest

# Worker image
docker build -f Dockerfile.worker -t customer-service-worker .
docker tag customer-service-worker:latest \
  <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/customer-service-worker:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/customer-service-worker:latest
```

---

## 4. Create RDS PostgreSQL

The app connects via `POSTGRES_CONNECTION_STRING` (see `app/src/core/config.py`) using asyncpg.

### 4.1 Create the database

1. Go to **RDS → Databases → Create database**.
2. Choose **PostgreSQL**, appropriate instance size.
3. Settings:
   - DB instance identifier: `customer-service-db`
   - Master username: `app`
   - Master password: (store securely)
4. Connectivity:
   - VPC: same VPC used for ECS.
   - Public access: **No**.
   - Security group: create `sg-customer-service-db` allowing inbound **5432** from the ECS tasks' security group (created in step 9).

### 4.2 Connection string

```text
postgresql://app:PASSWORD@customer-service-db.xxxxx.us-east-1.rds.amazonaws.com:5432/customer_service
```

Store this in **AWS Secrets Manager** and reference it in the ECS task definition.

---

## 5. Create ElastiCache for Redis

The app uses Redis for call session state and caching (see `app/src/infrastructure/redis.py`).

### 5.1 Create a Redis cluster

1. Go to **ElastiCache → Redis → Create**.
2. Cluster mode disabled (single primary node).
3. Name: `customer-service-redis`, node type e.g. `cache.t3.micro`.
4. Network: same VPC. Security group `sg-customer-service-redis` allowing inbound **6379** from the ECS tasks' security group.
5. Optionally enable **transit encryption** and **auth token**.

Note the **Primary endpoint** (e.g. `customer-service-redis.xxxxx.use1.cache.amazonaws.com`).

### 5.2 Redis environment variables

- `REDIS_HOST` = primary endpoint
- `REDIS_PORT` = `6379`
- `REDIS_PASSWORD` = auth token (if enabled), otherwise unset

---

## 6. Create Amazon MQ for RabbitMQ

The app uses RabbitMQ to decouple SendGrid inbound email processing from the synchronous HTTP handler (see `app/controllers/sendgrid.py` and `app/rabbitmq_worker.py`).

### 6.1 Create a RabbitMQ broker

1. Go to **Amazon MQ → Brokers → Create broker**.
2. Engine: **RabbitMQ**.
3. Broker name: `customer-service-mq`.
4. Instance type: e.g. `mq.t3.micro` (for dev) or larger for production.
5. Network: same VPC. Security group `sg-customer-service-mq` allowing:
   - Inbound **5672** (AMQP) from the ECS tasks' security group.
   - Inbound **15672** (management UI, optional, from your IP only).
6. Credentials: set username/password (store in Secrets Manager).

### 6.2 RabbitMQ environment variables

For the **app** container (publisher):
- `RABBITMQ_URL` = `amqp://<user>:<password>@<broker-endpoint>:5672/`

For the **worker** container (consumer):
- `RABBITMQ_HOST` = broker endpoint hostname
- `RABBITMQ_PORT` = `5672`
- `RABBITMQ_USER` = username
- `RABBITMQ_PASS` = password

The worker automatically declares two queues on startup:
- `sendgrid_email_inbound_queue` (main processing queue)
- `email_inbound_dlq` (dead-letter queue after 3 retries)

---

## 7. Milvus / Zilliz Cloud

The app uses Milvus for vector similarity search (see `app/src/infrastructure/milvus.py`). This is **not** an AWS service — use **Zilliz Cloud** (managed Milvus).

### 7.1 Set up Zilliz Cloud

1. Create a Zilliz Cloud account and provision a **Serverless** cluster in the same region.
2. Note the **cluster endpoint** (HTTPS URL including port 443) and the **API key**.

### 7.2 Milvus environment variables

- `MILVUS_CLUSTER_ENDPOINT` = `https://in03-xxxxx.cloud.zilliz.com:443`
- `MILVUS_COLLECTION_TOKEN` = your API key

These are already wired into `app/src/core/config.py` and `app/init_milvus.py`. If these are not set, Milvus is skipped gracefully.

---

## 8. Create an ECS cluster for Fargate

1. Go to **ECS → Clusters → Create cluster**.
2. Choose **Fargate** (networking only).
3. Cluster name: `customer-service-cluster`.
4. VPC: same VPC used for RDS, ElastiCache, and Amazon MQ.

---

## 9. Define the ECS task definitions

### 9.1 App task definition (`customer-service-task`)

1. **ECS → Task definitions → Create new task definition** → FARGATE.
2. Task definition name: `customer-service-task`.
3. CPU: `0.5 vCPU`, Memory: `1 GB` (adjust as needed).
4. Network mode: **awsvpc**.

**Container:**

| Setting | Value |
|---------|-------|
| Container name | `app` |
| Image | `<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/customer-service-agent:latest` |
| Port mappings | `8000/TCP` |

**Environment variables** (store secrets in Secrets Manager and reference via "Value from"):

| Variable | Source |
|----------|--------|
| `POSTGRES_CONNECTION_STRING` | Secrets Manager |
| `REDIS_HOST` | ElastiCache endpoint |
| `REDIS_PORT` | `6379` |
| `REDIS_PASSWORD` | Secrets Manager (if auth enabled) |
| `RABBITMQ_URL` | Secrets Manager (`amqp://user:pass@host:5672/`) |
| `MILVUS_CLUSTER_ENDPOINT` | Zilliz Cloud endpoint |
| `MILVUS_COLLECTION_TOKEN` | Secrets Manager |
| `OPENAI_API_KEY` | Secrets Manager |
| `TWILIO_ACCOUNT_SID` | Secrets Manager |
| `TWILIO_AUTH_TOKEN` | Secrets Manager |
| `TWILIO_PHONE_NUMBER` | plaintext or Secrets Manager |
| `SENDGRID_API_KEY` | Secrets Manager |
| `SENDGRID_FROM_EMAIL` | plaintext |
| `LANGSMITH_API_KEY` | Secrets Manager (optional) |
| `LANGSMITH_PROJECT` | plaintext (optional) |
| `LANGSMITH_TRACING` | `true` (optional) |
| `LANGSMITH_ENDPOINT` | plaintext (optional) |
| `LOG_LEVEL` | `INFO` |
| `ENVIRONMENT` | `production` |

### 9.2 Worker task definition (`customer-service-worker-task`)

1. Same task size as app (or smaller if appropriate).
2. Network mode: **awsvpc**.
3. No port mappings (the worker is a pure consumer, no HTTP server).

**Container:**

| Setting | Value |
|---------|-------|
| Container name | `worker` |
| Image | `<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/customer-service-worker:latest` |
| Port mappings | none |

**Environment variables** — same secrets as the app, except:

| Variable | Value |
|----------|-------|
| `RABBITMQ_HOST` | Amazon MQ broker hostname |
| `RABBITMQ_PORT` | `5672` |
| `RABBITMQ_USER` | Secrets Manager |
| `RABBITMQ_PASS` | Secrets Manager |

The worker also needs `POSTGRES_CONNECTION_STRING`, `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `MILVUS_CLUSTER_ENDPOINT`, `MILVUS_COLLECTION_TOKEN`, `OPENAI_API_KEY`, and any agent-related secrets — it initializes the same infrastructure as the app (see `app/rabbitmq_worker.py`).

---

## 10. Create an Application Load Balancer (ALB) with HTTPS

The ALB exposes the **app** service publicly over HTTPS. The worker has no ALB (it's a background consumer).

### 10.1 ACM certificate

1. **ACM → Request a certificate** for your domain (e.g. `api.example.com`).
2. Validate via DNS. Wait until **Issued**.

### 10.2 Create the ALB

1. **EC2 → Load Balancers → Create → Application Load Balancer**.
2. Name: `customer-service-alb`, Internet-facing, same VPC.
3. Security group `sg-customer-service-alb`:
   - Inbound **80** (HTTP) — optionally redirect to HTTPS
   - Inbound **443** (HTTPS)
4. Listeners:
   - HTTPS 443 → select ACM certificate → forward to target group

### 10.3 Target group

- Target type: **IP**
- Protocol: HTTP, Port: `8000`
- Health check path: `/api/health`
- Name: `customer-service-tg`

---

## 11. Create the ECS services

### 11.1 App service

1. **ECS → Clusters → customer-service-cluster → Create service** → FARGATE.
2. Task definition: `customer-service-task` (latest revision).
3. Service name: `customer-service-app`.
4. Desired tasks: `1` (scale as needed).
5. **Networking:**
   - Subnets: **private** subnets.
   - Security group: create `sg-customer-service-app` allowing:
     - Inbound **8000** from `sg-customer-service-alb`.
   - No public IP.
6. **Load balancing:** enable ALB, select `customer-service-alb`, target group `customer-service-tg`, container `app:8000`.

### 11.2 Worker service

1. **ECS → Clusters → customer-service-cluster → Create service** → FARGATE.
2. Task definition: `customer-service-worker-task` (latest revision).
3. Service name: `customer-service-worker`.
4. Desired tasks: `2` (matches `docker-compose.yml` `replicas: 2`).
5. **Networking:**
   - Subnets: **private** subnets.
   - Security group: `sg-customer-service-app` (reuse — same ingress rules apply for DB/Redis/MQ access).
   - No public IP.
6. **No load balancer** — the worker does not serve HTTP traffic.

### 11.3 Update security groups

Ensure these inbound rules exist:

| Security group | Port | Source |
|---------------|------|--------|
| `sg-customer-service-db` | 5432 | `sg-customer-service-app` |
| `sg-customer-service-redis` | 6379 | `sg-customer-service-app` |
| `sg-customer-service-mq` | 5672 | `sg-customer-service-app` |
| `sg-customer-service-app` | 8000 | `sg-customer-service-alb` |
| `sg-customer-service-alb` | 443 | `0.0.0.0/0` |
| `sg-customer-service-alb` | 80 | `0.0.0.0/0` |

---

## 12. DNS and webhook configuration

### 12.1 DNS

In **Route 53** (or your DNS provider):

- Type: **A (Alias)** or **CNAME**
- Name: `api.example.com`
- Target: ALB DNS name (e.g. `customer-service-alb-xxxxx.us-east-1.elb.amazonaws.com`)

### 12.2 ElevenLabs webhooks

In the **ElevenLabs** dashboard:

- Customer lookup URL: `https://api.example.com/api/elevenlabs/customer/{caller_phone_number}`
- Agent run URL: `https://api.example.com/api/elevenlabs/agent/run`
- Agent end URL: `https://api.example.com/api/elevenlabs/agent/end`

### 12.3 SendGrid webhooks

In the **SendGrid** dashboard → Inbound Parse:

- Destination URL: `https://api.example.com/api/sendgrid/inbound`
- Ensure the receiving domain is configured (e.g. `rxnorm.yourdomain.com`, `support.yourdomain.com`)

### 12.4 Twilio

In the **Twilio** dashboard, configure voice/webhook URLs pointing to your ElevenLabs agent (Twilio communicates with ElevenLabs, which then calls your app endpoints — not Twilio directly).

---

## 13. CI/CD

The project uses **GitHub Actions** (`.github/workflows/ci.yml`). On push to `main` or `dev`, it:

1. Creates `.env` from GitHub Secrets.
2. Builds the app Docker image.
3. Runs `pytest` inside the container against a real PostgreSQL and RabbitMQ.

### Production deployment flow

For automated deployments on merge to `main`:

1. **Build & push** both images to ECR (extend `ci.yml` or add a separate workflow).
2. **Update ECS service** to use the new task definition revision:
   ```bash
   aws ecs update-service \
     --cluster customer-service-cluster \
     --service customer-service-app \
     --task-definition customer-service-task \
     --force-new-deployment
   ```
3. Repeat for the worker service:
   ```bash
   aws ecs update-service \
     --cluster customer-service-cluster \
     --service customer-service-worker \
     --task-definition customer-service-worker-task \
     --force-new-deployment
   ```
4. ECS/ALB handle rolling deployment and health checks (`/api/health`).

---

## 14. Local development

- **Full stack**: `docker compose up` — starts PostgreSQL, RabbitMQ, app, and 2 worker replicas.
- **App only**: `uvicorn app.main:app --reload` (requires local PostgreSQL, Redis, and RabbitMQ).
- **Tunneling**: Use ngrok to expose `localhost:8000` for testing ElevenLabs/SendGrid webhooks without deploying.

---

## 15. Environment variable reference

| Variable | Required | Used by | Description |
|----------|----------|---------|-------------|
| `POSTGRES_CONNECTION_STRING` | Yes | app, worker | asyncpg connection string |
| `REDIS_HOST` | Yes | app, worker | Redis hostname |
| `REDIS_PORT` | Yes | app, worker | Redis port (default 6379) |
| `REDIS_PASSWORD` | No | app, worker | Redis auth (if enabled) |
| `RABBITMQ_URL` | Yes | app | AMQP URL for publishing messages |
| `RABBITMQ_HOST` | Yes | worker | RabbitMQ hostname |
| `RABBITMQ_PORT` | Yes | worker | RabbitMQ port (default 5672) |
| `RABBITMQ_USER` | Yes | worker | RabbitMQ username |
| `RABBITMQ_PASS` | Yes | worker | RabbitMQ password |
| `MILVUS_CLUSTER_ENDPOINT` | No | app, worker | Zilliz Cloud endpoint (skipped if unset) |
| `MILVUS_COLLECTION_TOKEN` | No | app, worker | Zilliz Cloud API key |
| `OPENAI_API_KEY` | Yes | app, worker | OpenAI API key for LLM calls |
| `TWILIO_ACCOUNT_SID` | Yes | app | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Yes | app | Twilio auth token |
| `TWILIO_PHONE_NUMBER` | Yes | app | Twilio phone number |
| `SENDGRID_API_KEY` | Yes | app | SendGrid API key for sending emails |
| `SENDGRID_FROM_EMAIL` | Yes | app | Sender email address |
| `LANGSMITH_API_KEY` | No | app, worker | LangSmith tracing |
| `LANGSMITH_PROJECT` | No | app, worker | LangSmith project name |
| `LANGSMITH_TRACING` | No | app, worker | Enable LangSmith tracing (`true`) |
| `LANGSMITH_ENDPOINT` | No | app, worker | LangSmith endpoint URL |
| `LOG_LEVEL` | No | app, worker | Logging level (default `INFO`) |
| `ENVIRONMENT` | No | app, worker | `development` or `production` |
