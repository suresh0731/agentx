# AgentX — STP Platform

End-to-end demo: LangGraph agent pipeline + Lit UI + SQLite in-memory seeded data.

## Quick Start (script)

From the project root on Windows:

```powershell
# First time only — installs Python and npm dependencies
.\scripts\start-local.ps1 -Setup

# Start backend + UI in separate console windows
.\scripts\start-local.ps1
```

Or double-click `start-local.bat`.

Open http://localhost:5173

## Manual Start (Windows)

You need **two PowerShell terminals** — one for the backend, one for the UI. Start the backend first.

### One-time setup

**Backend (Python)**

```powershell
cd agent-ingestion
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

**Frontend (Node)**

```powershell
cd agentx-ui
npm install
```

### Every time you run

**Terminal 1 — Backend (port 8001)**

```powershell
cd agent-ingestion
$env:PYTHONPATH = "src"
.\.venv\Scripts\uvicorn agentx.main:app --host 127.0.0.1 --port 8001 --reload
```

You should see:

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8001
```

Verify the backend:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
```

Expected response: `status = ok`

**Terminal 2 — UI (port 5173)**

```powershell
cd agentx-ui
npm run dev
```

You should see:

```
VITE v5.x.x  ready in ...
➜  Local:   http://localhost:5173/
```

Open http://localhost:5173 in your browser. The UI proxies API calls to the backend on port 8001.

### Checklist

| Step | What | URL |
|------|------|-----|
| 1 | Start backend first | http://127.0.0.1:8001/health |
| 2 | Start UI second | http://localhost:5173 |
| 3 | Open the app | http://localhost:5173 |

Keep both terminals open while working. Press `Ctrl+C` in each terminal to stop.

### Common issues

**Port already in use (`10048` on 8001 or 5173)**

Another process is using the port. Close the old terminal or stop the process:

```powershell
netstat -ano | findstr :8001
taskkill /PID <pid> /F
```

**`ModuleNotFoundError: agentx`**

Set `PYTHONPATH` before starting uvicorn:

```powershell
$env:PYTHONPATH = "src"
```

**UI loads but API calls fail**

Confirm the backend is running:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
```

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
