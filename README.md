# AgentX — STP Platform

End-to-end demo: LangGraph agent pipeline + Lit UI + SQLite in-memory seeded data.

## Quick Start

### Backend (port 8001)

```powershell
cd agent-ingestion
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
$env:PYTHONPATH="src"
.\.venv\Scripts\uvicorn agentx.main:app --host 127.0.0.1 --port 8001 --reload
```

### Frontend (port 5173)

```powershell
cd agentx-ui
npm install
npm run dev
```

Open http://localhost:5173

## Architecture

- **Backend:** `src/agentx/` — FastAPI, LangGraph 3-block pipeline, AnalyticsService, OpsAssistantAgent
- **Frontend:** `agentx-ui/` — Lit 3 + TypeScript + Vite
- **Seed data:** `seed/demo_data.json` → SQLite on startup

## API

- `GET /api/v1/dashboard/*` — KPIs, journey health, channels
- `GET /api/v1/instructions`, `/exceptions`, `/workbench/requests`
- `POST /api/v1/ingest` — trigger pipeline
- `POST /api/v1/assistant/chat` — SSE chat
- `WS /api/v1/ws/ops` — live updates
