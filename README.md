Recent News Agent (A2A + FastAPI)

Overview

- A small Agent-to-Agent (A2A) FastAPI service that runs a “recent news” workflow.
- Given a query (e.g., “NVIDIA future earnings report — what to expect”), it:
  - Retrieves fresh news from at least two sources (Google News + Bing News via RSS).
  - Produces a descriptive summary (bullets with context) and appends raw links.
  - Optionally emails the report if an email address is provided.

Main Components

- main.py: A2A-compatible FastAPI server with HTTP and WebSocket endpoints. Registers the workflow handler.
- agents/data_agent.py: Pulls news from Google News + Bing RSS, deduplicates items.
- agents/analysis_agent.py: Builds a readable report from titles/snippets and appends links.
- agents/orchestrator.py: Coordinates retrieval → analysis → optional email sending.
- agents/protocols/protocol.py: A minimal A2A protocol model (messages, handlers).

Requirements

- Python: >= 3.11 (see pyproject.toml)
- uv package manager (recommended)
- SMTP credentials to send email (optional but required for emailing)

Install uv (macOS examples)

- Homebrew: brew install uv
- Script: curl -LsSf https://astral.sh/uv/install.sh | sh

Project Setup

1. Sync and create venv with uv:
   cd /Users/andrestavera/Desktop/recent_news
   uv sync

2. Create a .env with SMTP configuration (required for email). Example (Gmail):
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your@gmail.com
   SMTP_PASSWORD=your_app_password
   SMTP_FROM=your@gmail.com
   SMTP_STARTTLS=true
   Note: For Gmail, use an App Password.

Run the Server

- Hot reload:
  uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000

Key Endpoints

- GET / → Health/welcome
- GET /info → Current agent info
- GET /agents → Known agents
- POST /message → A2A HTTP message endpoint (used for the workflow)
- WS /ws/{agent} → WebSocket channel (optional)

Trigger the Workflow (Postman)

- Method: POST
- URL: http://127.0.0.1:8000/message
- Headers: Content-Type: application/json
- Body (raw JSON):
  {
  "message_type": "request",
  "sender_id": "postman-client",
  "payload": {
  "action": "workflow.news",
  "params": {
  "query": "NVIDIA future earnings report — what to expect",
  "email_to": "you@example.com"
  }
  }
  }

Expected Response (shape)

- message_type: "response"
- payload.result:
  - query: string
  - status: "workflow completed"
  - summary: multi-line descriptive bullets + “Links:” list
  - sources: array of { title, url, source }
  - emailed: true/false depending on email success

Notes

- If you don’t want to send an email, omit email_to in params.
- If emailed is false, check your .env SMTP values and restart the server.
- The service uses RSS (no API keys) for portability; you can swap in APIs if desired.
