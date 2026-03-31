# Getting Started

This guide walks you through setting up and running the Customer Service Agent application.

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- (Optional) Virtual environment tool (venv, conda, or virtualenv)

## Installation

### 1. Clone and Navigate to the Project

```bash
cd elevenlabs-customer-service-agent/app
```

### 2. Create Virtual Environment

```bash
python -m venv .venv

# On Windows
.venv\Scripts\activate

# On macOS/Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r ../requirements.txt
```

### 4. Set Up Environment Variables

Copy the example environment file and configure it:

```bash
cp ../.env.example ../.env
```

Edit `.env` with your actual values:

```env
# Database (asyncpg connection string)
POSTGRES_CONNECTION_STRING=postgresql://user:password@localhost:5432/customer_service

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# App
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### 5. Set Up Database

Create the PostgreSQL database:

```bash
psql -U postgres -c "CREATE DATABASE customer_service;"
```

The application will automatically create required tables on startup.

### 6. Configure Agents (Optional)

The application uses `agent_configs.json` to define agents. This file is in `.gitignore` and created automatically if missing. Default configuration includes:

- `customer_support_agent` - Handles customer inquiries
- `security_agent` - Handles security verification

To customize, edit `app/agent_configs.json`:

```json
[
  {
    "name": "customer_support_agent",
    "system_prompt": "path/to/prompt.md",
    "llm": "kimi-k2.5",
    "tools": ["retrieve_conversation_history", "store_conversation_history"],
    "db_uri": "POSTGRES_CONNECTION_STRING",
    "skill_names": ["customer_support_skill"]
  }
]
```

## Running the Application

### Development Mode

```bash
# From the app directory
cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/

### Production Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Verification

Test the application is running:

```bash
curl http://localhost:8000/
```

Expected response:
```json
{"service": "customer-service-agent", "docs": "/docs"}
```

## Webhook Endpoints

The application provides webhook endpoints for external services:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhooks/sendgrid-inbound` | POST | Receive inbound emails from SendGrid |

Configure these URLs in your respective service dashboards.

## Architecture Notes

- **FastAPI**: Main web framework providing the HTTP API
- **LangGraph**: Agent orchestration and conversation flow
- **PostgreSQL**: Persistent storage for conversation history and session data
- **Redis**: Caching and call state management
- **Twilio/ElevenLabs**: Configured externally on their dashboards to call this API

## Troubleshooting

### Database Connection Issues

Verify your `POSTGRES_CONNECTION_STRING` format:
```
postgresql://username:password@host:port/database
```

### Redis Connection Issues

Ensure Redis is running:
```bash
redis-cli ping  # Should return PONG
```

### Module Import Errors

Make sure you're running from the correct directory:
```bash
cd app  # Run from the app directory
uvicorn main:app --reload
```

### Port Already in Use

Change the port:
```bash
uvicorn main:app --reload --port 8001
```

## Development Workflow

1. Activate virtual environment
2. Make code changes
3. Run with `--reload` flag for auto-restart
4. Test via `/docs` interactive API or curl

## Next Steps

- See [architecture.md](architecture.md) for system design details
- See [api.md](api.md) for API endpoint documentation
- See [database.md](database.md) for database schema details
