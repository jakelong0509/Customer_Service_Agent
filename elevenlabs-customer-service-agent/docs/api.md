# API Documentation

This document describes the HTTP API endpoints for the Customer Service Agent.

**Base URL:** Configurable (e.g., `https://your-ngrok-url.ngrok-free.app`)

---

## Health Check

### GET /

Returns service information and link to API docs.

**Response:**
```json
{
  "service": "customer-service-agent",
  "docs": "/docs"
}
```

---

### GET /api/health

Health check for load balancers and readiness probes.

**Response:**
```json
{
  "status": "ok"
}
```

---

## ElevenLabs Integration

Located in: `app/controllers/elevenlabs_controller.py`

These endpoints are designed to be called by ElevenLabs (or Twilio) webhooks during voice calls.

---

### GET /api/elevenlabs/customer/{caller_phone_number}

Retrieves or creates a customer by phone number. Called by ElevenLabs at the start of a call.

**Parameters:**

| Parameter | Type | In | Description |
|-----------|------|-----|-------------|
| `caller_phone_number` | string | path | The caller's phone number (e.g., `+15551234567`) |

**Response:** `CustomerModel`

```json
{
  "id": 123,
  "phone": "+15551234567",
  "email": "customer@example.com",
  "name": "John Doe",
  "plan": "Premium",
  "status": "active"
}
```

If the customer doesn't exist, a new customer is created automatically with name "Unregistered Customer".

---

### POST /api/elevenlabs/agent/run

Runs the agent to process a user request during an active call.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `call_sid` | string | yes | The call session ID |
| `caller_phone_number` | string | yes | The caller's phone number |

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent_name` | string | yes | Name of the agent to run (e.g., `customer_support_agent`) |
| `request` | string | yes | The user's message/request |

**Response:** `AgentRunResponse`

```json
{
  "result": "I'll help you with that. Let me look up your account...",
  "is_error": false
}
```

**Example:**

```bash
curl -X POST "https://your-url.ngrok-free.app/api/elevenlabs/agent/run?call_sid=CA123&caller_phone_number=%2B15551234567" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "customer_support_agent",
    "request": "I need help with my bill"
  }'
```

---

### POST /api/elevenlabs/agent/end

Ends the call, cleans up conversation state, and stores conversation history.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `call_sid` | string | yes | The call session ID |
| `caller_phone_number` | string | yes | The caller's phone number |

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent_name` | string | yes | Name of the agent |
| `request` | string | yes | End-of-call message (usually empty or "call ended") |

**Response:** `AgentRunResponse`

```json
{
  "result": "Conversation stored. Goodbye!",
  "is_error": false
}
```

---

## Email Webhook

### POST /webhooks/sendgrid-inbound

Receives inbound emails from SendGrid.

**Content-Type:** `application/x-www-form-urlencoded`

**Form Fields:**

| Field | Description |
|-------|-------------|
| `from` | Sender email address |
| `to` | Recipient email address |
| `subject` | Email subject |
| `text` | Plain text body |
| `html` | HTML body |
| `headers` | Raw email headers |
| `attachments` | Attachments (if any) |
| `message_id` | Message ID for threading |

**Response:**

```json
{
  "status": "received"
}
```

**Note:** Returns HTTP 200 for SendGrid to acknowledge receipt. Email processing happens asynchronously.

---

## Interactive API Documentation

When the server is running, interactive API documentation is available at:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## Error Responses

All endpoints may return the following error responses:

| Status | Description |
|--------|-------------|
| `400` | Bad Request - Invalid parameters |
| `404` | Not Found - Customer or resource not found |
| `422` | Validation Error - Invalid request body |
| `500` | Internal Server Error |

**Error Response Format:**

```json
{
  "detail": "Error message describing what went wrong"
}
```
