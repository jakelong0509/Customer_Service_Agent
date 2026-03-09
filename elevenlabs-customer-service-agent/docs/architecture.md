# Architecture: Customer Service Agent (Tool API)

## Scope

- **This server** exposes only an **HTTP API for tools**. No WebSockets, no Twilio/ElevenLabs code.
- **Twilio** and **ElevenLabs** are configured on their dashboards. When they need to run a tool, they call our API.
- **Postgres** and **Redis** are used by the app (tools, optional cache/session).

```
┌─────────────────┐     POST /api/tools/run      ┌─────────────────────────────┐
│ Twilio /        │  { tool_name, parameters }   │ Our server                  │
│ ElevenLabs      │ ───────────────────────────► │ - Routes (health, tools)     │
│ (dashboard)     │ ◄─────────────────────────── │ - Tool dispatcher + registry│
└─────────────────┘  { result, is_error }        │ - Postgres, Redis           │
                                                 └─────────────────────────────┘
```

---

## Folders

| Path | Role |
|------|------|
| **`app/main.py`** | FastAPI app, lifespan (init/close DB + Redis), API router. |
| **`app/config.py`** | Database URL, Redis, log level, environment. |
| **`app/api/routes.py`** | GET /api/health, POST /api/tools/run. |
| **`app/services/tool_dispatcher.py`** | Dispatches tool_name + parameters to registry; returns string result. |
| **`app/tools/`** | Registry and tool modules (customer, support, handoff). |
| **`app/models/conversation.py`** | CallContext (optional call_sid, from_number, to_number). |
| **`app/infrastructure/`** | database.py (asyncpg), redis.py. |

---

## Flow

1. External system (Twilio/ElevenLabs or other) sends **POST /api/tools/run** with `tool_name` and `parameters`.
2. Routes build optional **CallContext** from body or headers, call **tool_dispatcher.dispatch()**.
3. Dispatcher runs the tool via the **registry**; tools may use Postgres/Redis.
4. Server returns **{ result, is_error }** to the caller.
