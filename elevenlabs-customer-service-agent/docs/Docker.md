# Docker Development Guide

This guide covers running the Customer Service Agent application using Docker Compose for local development.

---

## Services Overview

The Docker Compose setup includes:

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `app` | Built from Dockerfile | 8000 | FastAPI application |
| `db` | postgres:16-alpine | 5432 | PostgreSQL database |

---

## Quick Start

### 1. Build and Start All Services

```bash
docker-compose up --build
```

### 2. Start in Background (Detached Mode)

```bash
docker-compose up -d
```

### 3. View Logs

```bash
# All services
docker-compose logs -f

# Just the app
docker-compose logs -f app

# Just the database
docker-compose logs -f db
```

### 4. Stop Services

```bash
# Stop gracefully
docker-compose down

# Stop and remove volumes (database data)
docker-compose down -v
```

---

## Known Issues & Solutions

### Database Startup Timing

**Problem:** The app container starts before the database is fully initialized, causing connection errors on first run.

**Error Message:**
```
Connection refused
Is the server running on host "db" and accepting TCP/IP connections on port 5432?
```

**Solution Implemented:**

The `docker-compose.yml` includes a healthcheck that ensures the app waits for PostgreSQL to be ready:

```yaml
db:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 5s
    timeout: 5s
    retries: 5

app:
  depends_on:
    db:
      condition: service_healthy
```

This configuration:
- Checks every 5 seconds if PostgreSQL is accepting connections
- Retries up to 5 times (25 seconds max wait)
- Only starts the app after the database healthcheck passes

---

## Building Images

### Build All Images

```bash
docker-compose build
```

### Build Specific Service

```bash
docker-compose build app
```

### Rebuild and Start

```bash
docker-compose up --build --force-recreate
```

---

## Development Workflow

### Hot Reload for Development

The app code is not mounted as a volume by default (commented out in docker-compose.yml). To enable code changes without rebuilding:

```yaml
# In docker-compose.yml, uncomment:
app:
  volumes:
    - .:/main
  working_dir: /main
```

Then restart:
```bash
docker-compose down
docker-compose up
```

### Run Database Migrations

```bash
# Access the app container
docker-compose exec app bash

# Inside container, run migrations
python -m alembic upgrade head
```

### Access Database Console

```bash
# Access PostgreSQL directly
docker-compose exec db psql -U postgres -d Customer_Support_Agent
```

---

## Environment Variables

Docker Compose reads from your `.env` file. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_CONNECTION_STRING` | Required | Database connection URL |
| `REDIS_HOST` | localhost | Redis host (currently commented out) |
| `LOG_LEVEL` | INFO | Logging level |
| `ENVIRONMENT` | development | Environment name |

---

## Troubleshooting

### Container Won't Start

```bash
# Check container status
docker-compose ps

# View detailed logs
docker-compose logs app
```

### Database Connection Failed

1. Ensure database container is healthy:
   ```bash
   docker-compose ps
   ```
   Should show `db` state as `healthy`

2. Check environment variables in `.env`

3. Verify connection string format:
   ```
   postgresql://postgres:ZGpkXO8U8L!@db:5432/Customer_Support_Agent
   ```

### Port Already in Use

If port 8000 or 5432 is already used:

```yaml
# In docker-compose.yml, change ports:
app:
  ports:
    - "8001:8000"  # Maps host 8001 to container 8000

db:
  ports:
    - "5433:5432"  # Maps host 5433 to container 5432
```

### Clean Slate

Remove everything and start fresh:

```bash
# Stop and remove containers, networks, volumes
docker-compose down -v

# Remove all images
docker rmi $(docker images -q)

# Rebuild from scratch
docker-compose up --build
```

---

## Production Considerations

This Docker setup is intended for **local development only**. For production:

1. Use environment-specific database credentials
2. Enable Redis (currently commented out)
3. Add reverse proxy (nginx/traefik)
4. Use proper secrets management
5. Configure log aggregation
6. Set up health monitoring

---

## Useful Commands

| Command | Description |
|---------|-------------|
| `docker-compose up` | Start services in foreground |
| `docker-compose up -d` | Start services in background |
| `docker-compose down` | Stop and remove containers |
| `docker-compose down -v` | Stop and remove containers + volumes |
| `docker-compose build` | Build images without starting |
| `docker-compose ps` | List running containers |
| `docker-compose exec app bash` | Access app container shell |
| `docker-compose exec db psql -U postgres` | Access database |
| `docker-compose logs -f` | Follow logs |

---

## References

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
