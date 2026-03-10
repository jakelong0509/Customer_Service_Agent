## Deploying to AWS: ECS Fargate + RDS + ElastiCache

This document explains what the core AWS services are (ECS Fargate, RDS, ElastiCache) and then walks through an opinionated, minimal setup to deploy the Customer Service Agent.

---

## 1. Service overview

- **ECS Fargate**
  - **ECS (Elastic Container Service)** is AWS’s managed container orchestrator (an alternative to running Kubernetes yourself).
  - **Fargate** is the *serverless* compute option for ECS: you do **not** manage EC2 instances. You tell AWS “run this container with X CPU and Y memory,” and it provisions capacity for you and bills per second.
  - In this project, ECS Fargate runs the Docker image defined by the project’s `Dockerfile` and exposes port `8000` for HTTP traffic.

- **RDS (Relational Database Service)**
  - Managed relational databases (PostgreSQL, MySQL, etc.).
  - AWS handles backups, minor version upgrades, automated failover (multi‑AZ), and storage.
  - In this project, we use **RDS PostgreSQL** and point the `DATABASE_URL` (or `POSTGRES_CONNECTION_STRING`) setting at the RDS endpoint.

- **ElastiCache**
  - Managed in‑memory cache service for **Redis** or Memcached.
  - AWS manages clustering, failover, and patching for the cache nodes.
  - In this project, we use **ElastiCache for Redis** and configure `REDIS_HOST`, `REDIS_PORT`, and optionally `REDIS_PASSWORD`.

---

## 2. Prerequisites

- An AWS account with permissions to use:
  - ECR (Elastic Container Registry)
  - ECS (Fargate)
  - RDS (PostgreSQL)
  - ElastiCache (Redis)
  - EC2 (for load balancers and security groups)
  - ACM (for TLS certificates)
  - Route 53 or another DNS provider (for a custom domain, optional but recommended)
- AWS CLI configured locally (**optional but helpful**).
- Docker installed locally.
- This repo checked out and working locally (you can run `uvicorn app.main:app --reload` or `docker-compose up`).

Assumed region: **`us-east-1`** (adjust to your own region where needed).

---

## 3. Build and push the Docker image to ECR

The app already has a `Dockerfile` that:

- Uses Python 3.12 slim
- Installs `requirements.txt`
- Runs `uvicorn app.main:app` on port `8000`

### 3.1 Create an ECR repository

In the AWS Console:

1. Go to **ECR → Repositories → Create repository**.
2. Choose **Private**.
3. Name the repository, for example: `customer-service-agent`.
4. Click **Create repository**.

ECR will show you a repository URI like:

`<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/customer-service-agent`

### 3.2 Log in to ECR and push the image

From your local terminal (PowerShell, bash, etc.):

1. Log in to ECR:

```bash
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
```

2. Build and tag the image (from the `elevenlabs-customer-service-agent` directory):

```bash
docker build -t customer-service-agent .

docker tag customer-service-agent:latest \
  <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/customer-service-agent:latest
```

3. Push the image:

```bash
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/customer-service-agent:latest
```

You now have a versioned image in ECR ready for ECS Fargate.

---

## 4. Create RDS PostgreSQL

The app reads its DB connection from `DATABASE_URL` or `POSTGRES_CONNECTION_STRING` (see `app/config.py`). We will provision an RDS PostgreSQL instance and then construct a connection string.

### 4.1 Create the database

In the AWS Console:

1. Go to **RDS → Databases → Create database**.
2. Choose:
   - **Standard create**
   - Engine: **PostgreSQL**
   - Template: **Free tier** or a small instance type.
3. Settings:
   - DB instance identifier: `customer-service-db`
   - Master username: `app` (or any username you prefer)
   - Master password: a strong password (save this somewhere secure).
4. Connectivity:
   - VPC: choose the VPC you will use for ECS (can be the default VPC for a simple setup).
   - Public access: ideally **No** (only ECS tasks will access the DB).
   - Security group: create a new SG, for example `sg-customer-service-db`, that:
     - Allows **inbound 5432 (PostgreSQL)** from the ECS tasks’ security group (we will create that security group in a later step and then update this rule).

Create the database and wait for it to become available. Note the **endpoint** (something like `customer-service-db.xxxxx.us-east-1.rds.amazonaws.com`).

### 4.2 Construct the connection string

Use the pattern:

```text
postgresql://<user>:<password>@<endpoint>:5432/<database>
```

For example:

```text
postgresql://app:YOUR_PASSWORD@customer-service-db.xxxxx.us-east-1.rds.amazonaws.com:5432/customer_service
```

You will set this value into `DATABASE_URL` or `POSTGRES_CONNECTION_STRING` in the ECS task definition (preferably via Secrets Manager).

---

## 5. Create ElastiCache for Redis

The app uses Redis (see `app/infrastructure/redis.py` and `app/config.py`). We will provision a Redis cluster in ElastiCache and point the app to it.

### 5.1 Create a Redis cluster

In the AWS Console:

1. Go to **ElastiCache → Redis → Create**.
2. Choose:
   - Deployment option: **Cluster mode disabled** (simple single‑primary node).
   - Engine: latest compatible Redis version.
3. Cluster settings:
   - Name: `customer-service-redis`
   - Node type: a small instance, e.g. `cache.t3.micro` (adjust as needed).
4. Network:
   - VPC: same as RDS and ECS.
   - Subnets: use an appropriate subnet group in that VPC.
   - Security group: create `sg-customer-service-redis` that allows:
     - Inbound **6379** from the ECS tasks’ security group (to be created).
5. (Optional but recommended) Enable **transit encryption** and **auth token** for Redis:
   - If you enable auth token, note the token; this will become your `REDIS_PASSWORD`.

Create the cluster and wait until its status is “available.” Note the **Primary endpoint**, for example:

```text
customer-service-redis.xxxxx.use1.cache.amazonaws.com
```

### 5.2 Redis-related environment variables

Later, when defining the ECS task, configure:

- `REDIS_HOST=customer-service-redis.xxxxx.use1.cache.amazonaws.com`
- `REDIS_PORT=6379`
- `REDIS_PASSWORD=<your-auth-token-if-enabled>` (or leave unset if you did not enable auth)

---

## 6. Create an ECS cluster for Fargate

1. Go to **ECS → Clusters → Create cluster**.
2. Choose the **Fargate** cluster option (networking only).
3. Cluster name: `customer-service-cluster`.
4. VPC: same VPC you used for RDS and ElastiCache.
5. Create the cluster.

---

## 7. Define the ECS Fargate task

The task definition describes how to run your container on Fargate.

1. Go to **ECS → Task definitions → Create new task definition**.
2. Launch type: **FARGATE**.
3. Task definition name: `customer-service-task`.
4. Task size:
   - CPU: e.g. `0.5 vCPU`
   - Memory: e.g. `1 GB` or `2 GB`
5. Network mode: **awsvpc** (required for Fargate).

### 7.1 Add the application container

In the task definition:

1. Add container:
   - Container name: `app`
   - Image: ECR image you pushed, e.g.
     `<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/customer-service-agent:latest`
   - Port mappings:
     - Container port: `8000`
     - Protocol: `TCP`

2. Environment variables:
   - `DATABASE_URL` (or `POSTGRES_CONNECTION_STRING`) = your RDS connection string.
   - `REDIS_HOST` = your Redis primary endpoint.
   - `REDIS_PORT` = `6379`
   - `REDIS_PASSWORD` = Redis auth token (if you enabled auth).
   - `LOG_LEVEL` = `INFO`
   - `ENVIRONMENT` = `production`

   **Recommended:** Store secrets (DB password, Redis auth token) in **AWS Secrets Manager** or **SSM Parameter Store** and reference them via the **“Value from”** field instead of hard‑coding values in the task definition.

Save the task definition.

---

## 8. Create an Application Load Balancer (ALB) with HTTPS

The ALB will expose the service publicly over HTTPS and forward requests to the Fargate tasks on port 8000.

### 8.1 Create or use an ACM certificate

1. Go to **ACM → Request a certificate**.
2. Request a public certificate for your domain, e.g. `api.example.com`.
3. Validate the certificate using DNS (Route 53 can auto‑create the DNS records).
4. Wait until the certificate status is **Issued**.

### 8.2 Create the ALB

1. Go to **EC2 → Load Balancers → Create load balancer → Application Load Balancer**.
2. Settings:
   - Name: `customer-service-alb`
   - Scheme: **Internet-facing**
   - IP type: IPv4
   - VPC: same VPC as ECS/RDS/ElastiCache
   - Subnets: select at least two public subnets
3. Security group:
   - Create `sg-customer-service-alb` that allows:
     - Inbound **80 (HTTP)** from the internet
     - Inbound **443 (HTTPS)** from the internet
4. Listeners:
   - HTTP 80: optionally configure a redirect to HTTPS 443
   - HTTPS 443:
     - Select the ACM certificate for `api.example.com`
     - Forward to a target group (you can create a new target group here, see below)

### 8.3 Create a target group

1. Target type: **IP**
2. Protocol: HTTP
3. Port: `8000`
4. Health check path: `/api/health`
5. Name: `customer-service-tg`

The ECS service will register task IPs in this target group, and the ALB health checks the `/api/health` endpoint.

---

## 9. Create the ECS service and wire it to the ALB

1. Go to **ECS → Clusters → customer-service-cluster → Create service**.
2. Launch type: **FARGATE**.
3. Task definition: choose `customer-service-task` (latest revision).
4. Service name: `customer-service`.
5. Desired tasks: `1` (you can scale later).

### 9.1 Networking and security groups

1. VPC: same VPC.
2. Subnets: choose **private** subnets (recommended) so the tasks are not directly internet‑exposed.
3. Assign a security group for the tasks, e.g. `sg-customer-service-app` that:
   - Allows **inbound 8000** from `sg-customer-service-alb` (the ALB’s SG).
4. Do **not** assign a public IP; the ALB provides public access.

Update the RDS and ElastiCache security groups so that:

- `sg-customer-service-db` allows inbound 5432 from `sg-customer-service-app`.
- `sg-customer-service-redis` allows inbound 6379 from `sg-customer-service-app`.

### 9.2 Load balancing configuration

1. In the ECS service wizard, enable **Application Load Balancer**.
2. Select:
   - Load balancer: `customer-service-alb`
   - Listener: HTTPS 443
   - Target group: `customer-service-tg`
   - Container to load balance: `app` on port `8000`

Create the service. ECS will start the Fargate task, register its IP in the target group, and the ALB will begin health checks.

When the task is healthy, you should see the target in the target group marked as **healthy**.

---

## 10. DNS and webhook configuration

### 10.1 DNS / custom domain

1. In **Route 53** (or your DNS provider), create a DNS record:
   - Type: **A (Alias)** or **CNAME**
   - Name: `api.example.com`
   - Target: the ALB’s DNS name (e.g. `customer-service-alb-xxxxx.us-east-1.elb.amazonaws.com`)
2. Wait for DNS to propagate.

You should now be able to reach:

- `https://api.example.com/api/health`
- `https://api.example.com/api/tools/run`

### 10.2 Configure Twilio and ElevenLabs webhooks

In the Twilio and ElevenLabs dashboards:

- Set the webhook / tool endpoint to:
  - `https://api.example.com/api/tools/run`
- Use `https://api.example.com/api/health` for health checks if required by your infrastructure or monitoring.

---

## 11. Deployment and iteration workflow

- **Local development and testing**:
  - Run the app locally via `uvicorn app.main:app --reload` or `docker-compose up`.
  - Use tools like ngrok to tunnel a public HTTPS URL to your local instance for testing Twilio/ElevenLabs without redeploying.
- **Cloud deployment (AWS)**:
  - Build and push a new image to ECR.
  - Update the ECS service to use the new task definition revision (or use a CI/CD pipeline to automate this on `main` branch pushes).
  - ECS/ALB handle rolling out the new version and health checking `/api/health`.

This setup gives you:

- A managed, production‑grade environment (ECS Fargate + RDS + ElastiCache).
- HTTPS and a stable public URL via ALB + ACM + DNS.
- A clean separation between local iteration and cloud deployment.

