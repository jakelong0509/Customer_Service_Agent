# System Design Walkthrough (General Principles)

A comprehensive guide to designing scalable, reliable, and maintainable systems.

---

## Table of Contents

1. [What is System Design?](#what-is-system-design)
2. [Core Concepts](#core-concepts)
3. [Scalability Fundamentals](#scalability-fundamentals)
4. [Database Design](#database-design)
5. [Caching Strategies](#caching-strategies)
6. [Load Balancing](#load-balancing)
7. [Microservices Architecture](#microservices-architecture)
8. [Message Queues](#message-queues)
9. [API Design](#api-design)
10. [Security Considerations](#security-considerations)
11. [Monitoring & Observability](#monitoring--observability)
12. [Common Design Patterns](#common-design-patterns)
13. [Real-World Examples](#real-world-examples)

---

## What is System Design?

**System Design** is the process of defining the architecture, components, modules, interfaces, and data for a system to satisfy specified requirements. It's about making trade-offs between:

- **Scalability** - Can it handle growth?
- **Reliability** - Will it stay up?
- **Performance** - Is it fast enough?
- **Maintainability** - Can we change it easily?
- **Cost** - Is it affordable?

### The Design Process

```
1. Requirements Gathering
   ├── Functional requirements (what it must do)
   └── Non-functional requirements (how well it must do it)

2. Capacity Estimation
   ├── Traffic estimates (QPS, DAU)
   │   ├── QPS (Queries Per Second): Requests handled per second
   │   └── DAU (Daily Active Users): Unique users per day
   ├── Storage estimates
   └── Bandwidth estimates

3. High-Level Design
   ├── System components
   ├── Data flow
   └── API definitions

4. Deep Dive
   ├── Database schema
   ├── Caching strategy
   ├── Load balancing
   └── Failure handling

5. Trade-off Analysis
   ├── CAP theorem decisions
   └── Cost vs performance
```

---

## Core Concepts

### The CAP Theorem

You can only guarantee **two out of three**:

| Property | Description | Example |
|----------|-------------|---------|
| **C**onsistency | Every read gets the most recent write | Bank transactions |
| **A**vailability | Every request gets a response | Social media feeds |
| **P**artition Tolerance | System works despite network failures | Distributed systems |

**Common Trade-offs:**
- **CP Systems**: MongoDB, HBase, Redis Cluster (consistency over availability)
- **AP Systems**: Cassandra, DynamoDB, CouchDB (availability over consistency)

### The PACELC Theorem (Extended CAP)

```
If Partitioned (P):
    Choose between Availability (A) or Consistency (C)
Else (E):
    Choose between Latency (L) or Consistency (C)
```

### Consistency Models

| Model | Description | Use Case |
|-------|-------------|----------|
| **Strong Consistency** | All nodes see same data immediately | Financial transactions |
| **Eventual Consistency** | Data will be consistent... eventually | Social media likes |
| **Causal Consistency** | Related operations are ordered | Chat applications |
| **Read-Your-Writes** | You always see your own updates | User profile updates |

---

## Scalability Fundamentals

### Vertical vs Horizontal Scaling

```
Vertical Scaling (Scale Up)          Horizontal Scaling (Scale Out)
═══════════════════════════════      ═══════════════════════════════
┌─────────────────────────┐           ┌─────────┐ ┌─────────┐ ┌─────────┐
│    Bigger Server        │           │ Server  │ │ Server  │ │ Server  │
│  ┌───────────────────┐  │           │   1     │ │   2     │ │   N     │
│  │   More CPU        │  │           └────┬────┘ └────┬────┘ └────┬────┘
│  │   More RAM        │  │                └─────────────┴───────────┘
│  │   More Disk       │  │                          │
│  └───────────────────┘  │                    Load Balancer
└─────────────────────────┘                          │
                                                ┌────┴────┐
                                                │  Users  │
                                                └─────────┘
```

| Aspect | Vertical | Horizontal |
|--------|----------|------------|
| **Limit** | Hardware ceiling | Nearly unlimited |
| **Downtime** | Usually required | Zero downtime |
| **Cost** | Expensive hardware | Commodity hardware |
| **Complexity** | Simple | Requires load balancing |
| **Single Point of Failure** | Yes | No |

### Scaling Patterns

#### 1. Database Scaling

**Read Replicas**
```
┌─────────────┐         ┌──────────────┐
│   Writes    │────────▶│ Primary DB   │
│             │         │  (Master)    │
└─────────────┘         └──────┬───────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ┌──────────┐     ┌──────────┐    ┌──────────┐
        │ Replica  │     │ Replica  │    │ Replica  │
        │    1     │     │    2     │    │    N     │
        └──────────┘     └──────────┘    └──────────┘
              │                │                │
              └────────────────┴────────────────┘
                               │
                        ┌─────────────┐
                        │    Reads    │
                        └─────────────┘
```

**Sharding**
```
User ID % 4 = Shard Number

Shard 0: Users 0, 4, 8...    Shard 1: Users 1, 5, 9...
┌─────────────┐              ┌─────────────┐
│  User Data  │              │  User Data  │
└─────────────┘              └─────────────┘

Shard 2: Users 2, 6, 10...   Shard 3: Users 3, 7, 11...
┌─────────────┐              ┌─────────────┐
│  User Data  │              │  User Data  │
└─────────────┘              └─────────────┘
```

#### 2. Application Scaling

**Stateless Services**
```
Any server can handle any request

Request 1 ──▶ Server A    Request 2 ──▶ Server B
Request 3 ──▶ Server C    Request 4 ──▶ Server A

Servers don't store session data
Session stored in: Redis / Database / JWT Token
```

**Auto-Scaling**
```
Metric-based scaling:

CPU > 70% for 5 min ──┐
                     ▼
            ┌─────────────────┐
            │  Add Instances  │
            └─────────────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ Load Balancer   │
            │  Distributes    │
            └─────────────────┘
```

---

## Database Design

### SQL vs NoSQL

| Aspect | SQL (Relational) | NoSQL (Non-relational) |
|--------|------------------|----------------------|
| **Structure** | Tables, rows, columns | Documents, key-value, graphs |
| **Schema** | Rigid, predefined | Flexible, dynamic |
| **Scaling** | Vertical + Read replicas | Horizontal (native) |
| **Joins** | Yes, efficient | Limited or none |
| **Transactions** | ACID compliance | BASE, eventual consistency |
| **Examples** | PostgreSQL, MySQL | MongoDB, Cassandra, Redis |
| **Best For** | Complex queries, relationships | High volume, unstructured data |

### Database Selection Guide

```
What is your data like?
│
├─ Structured with relationships?
│  └─ SQL (PostgreSQL, MySQL)
│
├─ Document-like, evolving schema?
│  └─ Document DB (MongoDB, CouchDB)
│
├─ Key-value access patterns?
│  └─ Key-Value Store (Redis, DynamoDB)
│
├─ Time-series data?
│  └─ Time-Series DB (InfluxDB, TimescaleDB)
│
├─ Graph relationships?
│  └─ Graph DB (Neo4j, Amazon Neptune)
│
└─ Wide-column, massive scale?
   └─ Wide-Column (Cassandra, HBase)
```

### Indexing Strategies

**B-Tree Index** (default for most SQL databases)
```
Balanced tree structure
┌─────────┐
│   50    │
└────┬────┘
┌────┴────┐
│         │
├────┼────┤      ├────┼────┤
│ 25 │ 40 │      │ 60 │ 75 │
└────┴────┘      └────┴────┘

Best for: Range queries, equality searches
```

**Hash Index**
```
Key ──▶ Hash Function ──▶ Index Position

Direct lookup, O(1) time
Best for: Exact match queries
Cannot do: Range queries
```

**Composite Index**
```sql
CREATE INDEX idx_name ON users(last_name, first_name);

Query: WHERE last_name = 'Smith' AND first_name = 'John' ✓
Query: WHERE last_name = 'Smith' ✓ (prefix)
Query: WHERE first_name = 'John' ✗ (not prefix)
```

---

## Caching Strategies

### Cache Placement

```
┌─────────────────────────────────────────────────────────┐
│                      Client Cache                       │
│              (Browser, Mobile App)                      │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   CDN Cache (Edge)                      │
│         (CloudFlare, AWS CloudFront, Fastly)           │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                Load Balancer Cache                      │
│              (Nginx, HAProxy cache)                     │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 Application Cache                       │
│                   (In-memory)                           │
│              (Caffeine, Guava Cache)                    │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 Distributed Cache                       │
│              (Redis, Memcached)                         │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   Database                              │
└─────────────────────────────────────────────────────────┘
```

### Caching Patterns

#### 1. Cache-Aside (Lazy Loading)
```
Application checks cache first

1. App ──▶ Cache: "Get user:123"
2. Cache miss ──▶ App
3. App ──▶ DB: "Get user:123"
4. App ──▶ Cache: "Store user:123"
5. Return to client

Pros: Simple, cache only contains requested data
Cons: Initial requests are slow (cache miss penalty)
```

#### 2. Write-Through
```
Data written to cache and DB simultaneously

1. App ──▶ Cache: "Set user:123"
2. Cache ──▶ DB: "Write user:123"
3. Cache ──▶ App: "Success"

Pros: Cache always fresh, no stale data
Cons: Write latency increases (must write to both)
```

#### 3. Write-Behind (Write-Back)
```
Data written to cache first, async to DB

1. App ──▶ Cache: "Set user:123"
2. Cache ──▶ App: "Success" (immediately)
3. Cache (async) ──▶ DB: "Write user:123"

Pros: Fast writes, reduced DB load
Cons: Risk of data loss if cache fails before DB write
```

#### 4. Read-Through
```
Cache manages DB interaction

1. App ──▶ Cache: "Get user:123"
2. Cache miss: Cache automatically fetches from DB
3. Cache ──▶ App: Data

Pros: Application logic simpler
Cons: Cache must support this pattern
```

### Cache Eviction Policies

| Policy | Description | Best For |
|--------|-------------|----------|
| **LRU** (Least Recently Used) | Remove least recently accessed | General purpose |
| **LFU** (Least Frequently Used) | Remove least often accessed | Hot data stays |
| **FIFO** (First In First Out) | Remove oldest added | Time-based data |
| **TTL** (Time To Live) | Expire after fixed time | Session data |
| **Random** | Remove random item | Simple implementation |

---

## Load Balancing

### Types of Load Balancers

#### Layer 4 (Transport Layer)
```
OSI Layer 4: TCP/UDP
Decisions based on: IP address, Port, Protocol

┌─────────────┐
│   Client    │
└──────┬──────┘
       │ TCP Connection
       ▼
┌─────────────┐
│ L4 Load     │──┐
│ Balancer    │  │──▶ Server 1 (IP:Port)
└─────────────┘  │
                 ├──▶ Server 2 (IP:Port)
                 │
                 └──▶ Server 3 (IP:Port)

Fast, no content inspection
Examples: AWS NLB, HAProxy (L4 mode)
```

#### Layer 7 (Application Layer)
```
OSI Layer 7: HTTP/HTTPS
Decisions based on: URL, Header, Cookies, Content

┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP Request
       ▼
┌─────────────┐
│ L7 Load     │──┐
│ Balancer    │  │──▶ API Servers
└─────────────┘  │
                 ├──▶ Static File Servers
                 │
                 └──▶ WebSocket Servers

Can route: /api/* → API servers
           /static/* → CDN
           /ws/* → WebSocket servers

Examples: AWS ALB, Nginx, HAProxy (L7 mode)
```

### Load Balancing Algorithms

| Algorithm | How It Works | Best For |
|-----------|--------------|----------|
| **Round Robin** | Sequential distribution | Equal capacity servers |
| **Weighted Round Robin** | Sequential with capacity weights | Unequal capacity |
| **Least Connections** | Route to server with fewest connections | Long-lived connections |
| **Least Response Time** | Route to fastest responding server | Performance optimization |
| **IP Hash** | Hash of client IP determines server | Session affinity |
| **Consistent Hashing** | Hash of key determines server | Caching, distributed systems |

### Health Checks

```
Load Balancer continuously checks server health:

┌─────────┐    Health Check    ┌─────────┐
│   LB    │───────────────────▶│ Server  │
│         │◀───────────────────│   1     │
└─────────┘   200 OK / Fail    └─────────┘

If server fails health check:
- Remove from pool
- Retry after cooldown
- Alert if threshold exceeded
```

---

## Microservices Architecture

### Monolith vs Microservices

```
Monolith                          Microservices
═════════                        ═════════════

┌──────────────────┐             ┌──────────┐
│   Single Code    │             │   API    │
│    Base          │             │ Gateway  │
└────────┬─────────┘             └────┬─────┘
         │                            │
    ┌────┴────┐              ┌────────┼────────┐
    │         │              ▼        ▼        ▼
┌───┴──┐ ┌───┴──┐      ┌────────┐ ┌────────┐ ┌────────┐
│Module│ │Module│      │Service │ │Service │ │Service │
│  A   │ │  B   │      │ Users  │ │ Orders │ │Payment │
└──────┘ └──────┘      └────┬───┘ └────┬───┘ └────┬───┘
                            │          │          │
                       ┌────┴──────────┴──────────┴────┐
                       │     Shared / Individual DBs    │
                       └─────────────────────────────────┘
```

### Service Communication Patterns

#### 1. Synchronous (Request/Response)
```
Service A ──HTTP/gRPC──▶ Service B
         ◀──Response───

Pros: Simple, immediate feedback
Cons: Tight coupling, cascading failures
```

#### 2. Asynchronous (Event-Driven)
```
Service A ──Event──▶ Message Queue ──▶ Service B
                                            │
                                            ▼
                                        Service C

Pros: Loose coupling, resilience, scalability
Cons: Complex debugging, eventual consistency
```

#### 3. Choreography vs Orchestration

**Choreography (Event Collaboration)**
```
Order Placed
     │
     ├──▶ Inventory Service (decrease stock)
     │
     ├──▶ Payment Service (process payment)
     │
     └──▶ Notification Service (send email)

Each service reacts to events independently
```

**Orchestration (Central Controller)**
```
                    ┌─────────────────┐
                    │  Orchestrator   │
                    │  (Saga Manager) │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   Inventory   │    │   Payment     │    │  Notification │
│   Service     │    │   Service     │    │   Service     │
└───────────────┘    └───────────────┘    └───────────────┘

Orchestrator directs each step
```

### Service Discovery

```
Service Startup:
┌──────────────┐
│  Service A   │──Register──▶┌──────────────┐
│  (Instance 1)│              │   Service    │
└──────────────┘              │  Registry    │
                              │ (Consul,     │
                              │  Eureka,     │
                              │  Kubernetes) │
                              └──────────────┘

Service Discovery:
┌──────────────┐            ┌──────────────┐
│  Service B   │──Query───▶│   Service    │
│  (Needs A)   │◀──IPs─────│  Registry    │
└──────────────┘            └──────────────┘

Load Balancing:
Client-side or Server-side LB distributes across instances
```

---

## Message Queues

### Queue Patterns

#### 1. Point-to-Point (Queue)
```
Producer ──▶ Queue ──▶ One Consumer

Each message processed by exactly one consumer
Good for: Task distribution, work queues
```

#### 2. Publish-Subscribe (Topic)
```
         ┌────────▶ Consumer A
Producer ─┼────────▶ Consumer B
         └────────▶ Consumer C

Each message received by all subscribers
Good for: Event broadcasting, notifications
```

#### 3. Message Streaming
```
Partitioned Log (like Kafka)

Partition 0: [m1]─[m2]─[m3]─► Consumer Group A
Partition 1: [m4]─[m5]─[m6]─► Consumer Group B

Consumers read from offsets
Replay capability
High throughput
```

### Message Queue Selection

| Queue | Type | Best For |
|-------|------|----------|
| **RabbitMQ** | Traditional queue | Complex routing, reliability |
| **Kafka** | Streaming | High throughput, log aggregation |
| **Redis Pub/Sub** | In-memory | Real-time, low latency |
| **SQS** | Managed cloud | AWS ecosystem, simplicity |
| **ActiveMQ** | Traditional queue | JMS compliance |

### Backpressure Handling

```
When consumers can't keep up:

Producer ──▶ Queue ──▶ Consumers
              │
              └──▶ Overflow strategies:
                   1. Drop oldest (if acceptable)
                   2. Reject new (block producer)
                   3. Scale consumers (auto-scaling)
                   4. Dead letter queue (DLQ)
```

---

## API Design

### REST vs GraphQL vs gRPC

| Aspect | REST | GraphQL | gRPC |
|--------|------|---------|------|
| **Protocol** | HTTP/1.1 | HTTP/1.1 or HTTP/2 | HTTP/2 |
| **Format** | JSON | JSON | Protocol Buffers |
| **Style** | Resource-based | Query-based | Service/Method |
| **Flexibility** | Fixed endpoints | Client specifies fields | Fixed contracts |
| **Performance** | Good | Good | Excellent |
| **Caching** | Easy (HTTP) | Hard | Limited |
| **Best For** | Public APIs, web | Mobile, complex data | Internal services |

### REST API Design Principles

```
Resources (nouns):
GET    /users          # List users
GET    /users/123      # Get specific user
POST   /users          # Create user
PUT    /users/123      # Update user (full)
PATCH  /users/123      # Update user (partial)
DELETE /users/123      # Delete user

Nested resources:
GET /users/123/orders   # Get user's orders
```

### API Versioning Strategies

| Strategy | Example | Pros | Cons |
|----------|---------|------|------|
| **URL** | `/v1/users` | Simple, explicit | Clutters URL |
| **Header** | `Accept: v1+json` | Clean URL | Harder to test |
| **Query** | `/users?version=1` | Simple | Not standard |

### Rate Limiting

```
Algorithms:

1. Token Bucket
   ┌─────────┐
   │ Tokens  │──▶ Requests consume tokens
   │ refill  │──▶ Tokens refill at fixed rate
   │  rate   │
   └─────────┘

2. Leaky Bucket
   ┌─────────┐
   │  Queue  │──▶ Smooth output rate
   │ (fixed  │──▶ Excess requests queued/dropped
   │  size)  │
   └─────────┘

3. Fixed Window
   Count requests in time window
   Reset at window boundary

4. Sliding Window
   More accurate, tracks exact time
   Higher memory cost
```

---

## Security Considerations

### Authentication & Authorization

```
Authentication: Who are you?
Authorization: What can you do?

OAuth 2.0 Flow:
┌─────────┐                              ┌─────────┐
│  User   │──Login──────────────────────▶│  Auth   │
│         │                              │ Server  │
│         │◀─Authorization Code─────────│         │
│         │                              │         │
│  Client │──Code + Secret───────────────▶│         │
│         │◀─Access Token + Refresh─────│         │
│         │                              │         │
│         │──API Call w/ Token──────────▶│  API    │
│         │◀─Data───────────────────────│         │
└─────────┘                              └─────────┘

JWT Structure:
Header.Payload.Signature
 eyJhbG...eyJ1c2Vy...SflKxw...
```

### Security Best Practices

| Layer | Measures |
|-------|----------|
| **Network** | HTTPS/TLS, VPC, Security Groups, WAF |
| **Application** | Input validation, Parameterized queries, CSRF tokens |
| **Data** | Encryption at rest, Encryption in transit, Hash passwords |
| **API** | Rate limiting, API keys, OAuth 2.0, JWT |
| **Infrastructure** | Secrets management, Least privilege, MFA |

### Common Vulnerabilities

| Vulnerability | Prevention |
|---------------|------------|
| **SQL Injection** | Parameterized queries, ORM |
| **XSS** | Input sanitization, CSP headers |
| **CSRF** | CSRF tokens, SameSite cookies |
| **MITM** | HTTPS/TLS everywhere |
| **DoS** | Rate limiting, CDN, WAF |

---

## Monitoring & Observability

### The Three Pillars

```
┌─────────────────────────────────────────────────────────┐
│                    Observability                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐  │
│   │   Metrics   │   │    Logs     │   │   Traces    │  │
│   │             │   │             │   │             │  │
│   │  "What"     │   │   "Why"     │   │  "Where"    │  │
│   │  CPU: 80%   │   │ Error in    │   │ Request     │  │
│   │  QPS: 1000  │   │ line 42     │   │ path A→B→C  │  │
│   │  Latency:   │   │ User 123    │   │ Duration    │  │
│   │  200ms      │   │ failed auth │   │  150ms      │  │
│   └─────────────┘   └─────────────┘   └─────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Key Metrics (The Four Golden Signals)

| Signal | What to Track |
|--------|---------------|
| **Latency** | Response time, percentiles (p50, p95, p99) |
| **Traffic** | Requests per second, concurrent users |
| **Errors** | Error rate, error types, status codes |
| **Saturation** | CPU, memory, disk, network utilization |

### Alerting Strategy

```
Alert Levels:

INFO    ──▶ Dashboard update only
WARNING ──▶ Slack notification
CRITICAL ──▶ PagerDuty alert

Alert Conditions:
- Error rate > 1% for 5 minutes
- P99 latency > 500ms for 10 minutes
- CPU > 80% for 15 minutes
- Failed health checks
```

---

## Common Design Patterns

### 1. Circuit Breaker

```
Normal State:        Open State (Failing):
┌─────────┐          ┌─────────┐
│ Service │──Call──▶ │ Service │──X──▶ (fail fast)
│    A    │◀─Success─│    B    │
└─────────┘          └─────────┘
                            │
                     Half-Open (Testing):
                     ┌─────────┐
                     │ Service │──Test──▶
                     │    B    │◀─────────
                     └─────────┘

States: CLOSED (normal) → OPEN (failing) → HALF-OPEN (testing)
```

### 2. Bulkhead

```
Isolate failures:

┌─────────────────────────┐
│        System           │
├─────────┬─────────┬─────┤
│Pool A   │ Pool B  │PoolC│
│Users    │ Orders  │Pay  │
├─────────┼─────────┼─────┤
│████░░░░░│█████████│░░░░░│
│ Error   │   OK    │ OK  │
└─────────┴─────────┴─────┘

Failure in one pool doesn't affect others
```

### 3. Retry with Exponential Backoff

```
Retry Pattern:

Attempt 1: Fail ──▶ Wait 1s ──▶ Retry
Attempt 2: Fail ──▶ Wait 2s ──▶ Retry
Attempt 3: Fail ──▶ Wait 4s ──▶ Retry
Attempt 4: Fail ──▶ Wait 8s ──▶ Retry
Attempt 5: Fail ──▶ Circuit Breaker

With Jitter: Randomize wait time to avoid thundering herd
```

### 4. Saga Pattern (Distributed Transactions)

```
Compensating Transactions:

Step 1: Reserve Payment ──▶ Success
Step 2: Create Order ──────▶ Success
Step 3: Reserve Inventory ─▶ FAIL

Compensation:
Step 2: Cancel Order ──────▶ Success
Step 1: Refund Payment ────▶ Success

System returns to consistent state
```

### 5. CQRS (Command Query Responsibility Segregation)

```
Separate read and write models:

Writes (Commands)           Reads (Queries)
┌─────────┐                 ┌─────────┐
│ Command │──▶ Write DB     │  Query  │◀── Read DB
│ Handler │    (normalized) │ Handler │    (denormalized)
└─────────┘                 └─────────┘
      │                           │
      └──────────Event Bus────────┘
            (syncs read model)

Write optimized for consistency
Read optimized for speed
```

### 6. Event Sourcing

```
Store events, not state:

Traditional:          Event Sourcing:
┌─────────┐          ┌─────────────────┐
│ User    │          │ UserCreated     │
│ state:  │          │ NameChanged     │
│ name:Bob│          │ EmailChanged    │
│ email:..│          │ AddressChanged  │
└─────────┘          └─────────────────┘
                            │
                            ▼
                     ┌─────────────┐
                     │ Current     │
                     │ State       │
                     │ (projection)│
                     └─────────────┘

Benefits: Complete audit trail, temporal queries, replay capability
```

---

## Real-World Examples

### Example 1: URL Shortener (TinyURL)

```
Requirements:
- Shorten long URLs
- Redirect short to long
- 100M URLs, 1B reads/day

Design:
┌─────────┐    ┌───────────────┐    ┌─────────┐
│  User   │───▶│  Load Balancer │───▶│   API   │
│         │◀───│               │◀───│ Servers │
└─────────┘    └───────────────┘    └────┬────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
              ┌──────────┐         ┌──────────┐        ┌──────────┐
              │  Cache   │         │   DB     │        │  Cache   │
              │ (Redis)  │         │(Postgres)│        │  (CDN)   │
              └──────────┘         └──────────┘        └──────────┘

Key Decisions:
- Base62 encoding for short IDs (e.g., abc123)
- Cache hot URLs in Redis
- Database sharding by ID range
- Read-through cache for redirects
```

### Example 2: Web Crawler

```
Components:

┌─────────────┐
│   Seed URLs │
└──────┬──────┘
       ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   URL       │───▶│   Crawler   │───▶│   Content   │
│   Frontier  │    │   Workers   │    │   Store     │
│   (Queue)   │◀───│             │◀───│             │
└─────────────┘    └─────────────┘    └─────────────┘
                                            │
                                            ▼
                                     ┌─────────────┐
                                     │   Indexer   │───▶ Search Index
                                     └─────────────┘

Design Points:
- Politeness: Respect robots.txt, rate limits
- Deduplication: Bloom filter for URL uniqueness
- Distributed: Multiple crawler workers
- Storage: S3 for raw content, Elasticsearch for index
```

### Example 3: Video Streaming (YouTube)

```
Architecture:

Upload Flow:                    Playback Flow:
┌─────────┐                     ┌─────────┐
│ Creator │                     │  User   │
└────┬────┘                     └────┬────┘
     │                              │
     ▼                              ▼
┌──────────┐                ┌──────────────┐
│ Upload   │                │   CDN Edge   │
│ Service  │                │   (Cache)    │
└────┬─────┘                └──────┬───────┘
     │                             │
     ▼                             │ Cache miss
┌──────────┐                       ▼
│ Encoder  │                ┌──────────────┐
│ (Multiple│                │  Origin      │
│ formats) │                │  Servers     │
└────┬─────┘                └──────────────┘
     │
     ▼
┌──────────┐
│ Storage  │
│ (Object) │
└──────────┘

Key Features:
- Multiple resolutions (240p to 4K)
- Adaptive bitrate streaming
- Global CDN distribution
- Video encoding pipeline
```

### Example 4: Ride Sharing (Uber)

```
Real-time System:

┌──────────┐                  ┌──────────┐
│  Rider   │◀──Match─────────▶│  Driver  │
│   App    │                  │   App    │
└────┬─────┘                  └────┬─────┘
     │                              │
     ▼                              ▼
┌───────────────────────────────────────┐
│         Real-time Services            │
│  ┌──────────┐    ┌──────────┐       │
│  │ Location │    │  Demand   │       │
│  │ Service  │    │ Prediction│       │
│  └──────────┘    └──────────┘       │
└───────────────────────────────────────┘
              │
              ▼
┌───────────────────────────────────────┐
│         Data Processing               │
│  Kafka / Spark Streaming / Analytics  │
└───────────────────────────────────────┘

Challenges:
- Real-time location updates
- Geospatial indexing (find drivers near rider)
- Surge pricing calculations
- ETA estimation
```

---

## Capacity Estimation Guide

### Quick Formulas

```
Storage Estimation:
Daily Active Users × Actions per user × Data per action × Retention days

Example:
10M DAU × 10 actions × 1KB × 365 days = 36.5TB/year

QPS Estimation:
DAU × Actions per day / Seconds in day × Peak multiplier

Example:
10M × 30 / 86400 × 3 (peak) = ~10,000 QPS peak

Bandwidth Estimation:
QPS × Average response size

Example:
10,000 × 10KB = 100MB/s = 800Mbps
```

### Back-of-Envelope Numbers

| Operation | Latency |
|-----------|---------|
| L1 cache reference | 0.5 ns |
| L2 cache reference | 7 ns |
| Main memory reference | 100 ns |
| SSD random read | 100 μs |
| SSD sequential read | 200 MB/s |
| Disk seek | 10 ms |
| Disk sequential read | 100 MB/s |
| Same datacenter network | 0.5 ms |
| Cross-country network | 50-150 ms |
| Intercontinental | 100-300 ms |

---

## Summary Checklist

When designing a system, ask:

**Scalability**
- [ ] Can it handle 10x growth?
- [ ] Is it horizontally scalable?
- [ ] Are there any single points of failure?

**Performance**
- [ ] What's the expected latency?
- [ ] Is caching implemented?
- [ ] Are database queries optimized?

**Reliability**
- [ ] What happens when components fail?
- [ ] Is there data replication?
- [ ] Are there health checks and auto-recovery?

**Security**
- [ ] Is data encrypted in transit and at rest?
- [ ] Is authentication and authorization implemented?
- [ ] Are inputs validated and sanitized?

**Maintainability**
- [ ] Is the architecture modular?
- [ ] Can components be deployed independently?
- [ ] Is there proper logging and monitoring?

**Cost**
- [ ] What's the infrastructure cost?
- [ ] Can it run on commodity hardware?
- [ ] Are there auto-scaling policies to save costs?

---

## Additional Resources

- **Books**: "Designing Data-Intensive Applications" by Martin Kleppmann
- **Papers**: Google Bigtable, Dynamo (Amazon), Spanner
- **Websites**: High Scalability blog, System Design Primer (GitHub)
- **Practice**: Design Twitter, Design Uber, Design WhatsApp

---

*This document provides a foundation for system design interviews and real-world architecture decisions. The key is understanding trade-offs and justifying decisions based on requirements.*