# ElevenLabs Customer Service Agent

Voice AI customer service agent integrating Twilio (calls) and ElevenLabs (conversational AI).

## Structure

- **app/** – Main application (FastAPI, API, services, tools, models, infrastructure, utils)
- **tests/** – Unit, integration tests and fixtures
- **scripts/** – Deploy and migration scripts
- **docs/** – Architecture and API documentation

## Setup

1. Copy `.env.example` to `.env` and set your credentials.
2. Install dependencies: `pip install -r requirements.txt`
3. Run locally: `uvicorn app.main:app --reload`
4. Or use Docker: `docker-compose up`

## Docs

- [Architecture](docs/architecture.md)
- [API](docs/api.md)
