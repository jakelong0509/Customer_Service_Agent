# API

## Health

- **GET /api/health**  
  Returns `{ "status": "ok" }`. Use for load balancers and readiness.

---

## Tools

- **POST /api/tools/run**

  Run a tool by name. Body (JSON):

  | Field | Type | Required | Description |
  |-------|------|----------|-------------|
  | `tool_name` | string | yes | e.g. `lookup_customer`, `create_ticket` |
  | `parameters` | object | no | Tool arguments (default `{}`) |
  | `call_sid` | string | no | Optional call/session ID |
  | `from_number` | string | no | Optional caller number |
  | `to_number` | string | no | Optional called number |

  Optional context can also be sent via headers: `X-Call-Sid`, `X-From`, `X-To`.

  **Response:** `{ "result": string, "is_error": boolean }`

  **Example:**

  ```json
  POST /api/tools/run
  { "tool_name": "lookup_customer", "parameters": { "phone_number": "+15551234567" } }
  ```

  ```json
  { "result": "Found customer: Jane Doe (ID 12345)", "is_error": false }
  ```
