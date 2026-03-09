# Customer Service Agent — Tool API

## Architecture (no WebSocket)

- **This server** exposes an **HTTP API for tools only**. No telephony or voice AI code runs here.
- **Twilio** and **ElevenLabs** are configured on their own dashboards (webhooks, flows, etc.). When they need to run a tool (e.g. lookup customer, create ticket), they call our API.
- **Postgres** and **Redis** are kept for tools and optional session/cache use.

```
┌─────────────┐                    ┌─────────────────────────────────┐
│  Twilio /   │  HTTP POST         │  Our server                      │
│ ElevenLabs  │  /api/tools/run    │  - FastAPI                       │
│ (dashboard  │ ─────────────────► │  - Tools (customer, support,     │
│  config)    │  { tool_name,      │    handoff)                      │
│             │    parameters }    │  - Postgres + Redis              │
└─────────────┘                    └─────────────────────────────────┘
```

---

## Folder overview

| Area | Role |
|------|------|
| **`app/main.py`** | FastAPI app, lifespan (init/close DB + Redis), mounts API router. |
| **`app/config.py`** | Settings: database URL, Redis host/port, log level, environment. No Twilio/ElevenLabs. |
| **`app/api/routes.py`** | **GET /api/health** and **POST /api/tools/run** (body: `tool_name`, `parameters`; optional context in body or headers). |
| **`app/services/tool_dispatcher.py`** | Dispatches by `tool_name` to the tool registry; returns a string result. |
| **`app/tools/`** | Registry and tool implementations (customer, support, handoff). |
| **`app/models/conversation.py`** | `CallContext` (optional call_sid, from_number, to_number) for tool calls. |
| **`app/infrastructure/`** | Postgres (asyncpg) and Redis clients. |

---

## Tool API

- **POST /api/tools/run**  
  - Body: `{ "tool_name": string, "parameters": object }`  
  - Optional context: `call_sid`, `from_number`, `to_number` in body or headers (`X-Call-Sid`, `X-From`, `X-To`).  
  - Response: `{ "result": string, "is_error": boolean }`.

Twilio or ElevenLabs (or any caller) send a request when they need to execute a tool; the server runs it and returns the result.

---

## Environment

See `.env.example`. Required: Postgres connection string, Redis host/port. Optional: Redis auth, `LOG_LEVEL`, `ENVIRONMENT`.

---

## Summary

- Server = **tool API only** (no WebSocket, no Twilio/ElevenLabs logic).
- Twilio and ElevenLabs are handled on their dashboards; they call our API to run tools.
- DB and Redis remain for tools and state/cache.
