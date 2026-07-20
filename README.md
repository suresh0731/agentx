# AgentX — STP Platform

End-to-end demo: LangGraph agent pipeline + Lit UI + SQLite in-memory seeded data.

## Quick Start (script)

From the project root on Windows:

```powershell
# First time only — creates .venv and installs dependencies
.\scripts\setup.ps1

# Start backend + UI in separate console windows
.\scripts\start-local.ps1
```

Or double-click `setup.bat` then `start-local.bat`.

Open http://localhost:5173

## Manual Start (Windows)

You need **two terminals** — one for the backend, one for the UI. Start the backend first.

Use **PowerShell** or **CMD** — the commands differ slightly for setting environment variables.

### One-time setup

> **Important:** `pip install` does **not** create `.venv`. You must create the virtual environment first with `python -m venv .venv`, then install packages **into** it.

**Option A — setup script (recommended)**

```powershell
cd agent-ingestion
.\scripts\setup.ps1
```

**Option B — manual commands**

**Backend (Python)** — run from the project root (`agent-ingestion`):

```powershell
cd agent-ingestion

# Step 1: create the virtual environment (required before pip install)
python -m venv .venv

# Step 2: verify .venv was created
Test-Path .\.venv\Scripts\python.exe   # should print True

# Step 3: install packages into .venv (not globally)
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

The last command (`pip install -e .`) registers the `agentx` package so you do **not** need to set `PYTHONPATH` every time.

**Frontend (Node)**

```powershell
cd agentx-ui
npm install
```

### Every time you run

**Terminal 1 — Reconciliation Service (port 8002)**

```cmd
cd agent-ingestion
set PYTHONPATH=src
.\.venv\Scripts\uvicorn recon_service.main:app --host 127.0.0.1 --port 8002 --reload
```

**Terminal 2 — Backend API (port 8001)**

After setup (`pip install -e .`), you can start uvicorn directly — no `PYTHONPATH` needed:

```cmd
cd agent-ingestion
.\.venv\Scripts\uvicorn agentx.main:app --host 127.0.0.1 --port 8001 --reload
```

If you skipped `pip install -e .`, set `PYTHONPATH` first:

PowerShell:

```powershell
cd agent-ingestion
$env:PYTHONPATH = "src"
.\.venv\Scripts\uvicorn agentx.main:app --host 127.0.0.1 --port 8001 --reload
```

CMD:

```cmd
cd agent-ingestion
set PYTHONPATH=src
.\.venv\Scripts\uvicorn agentx.main:app --host 127.0.0.1 --port 8001 --reload
```

You should see:

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8001
```

Verify the backend:

```cmd
curl http://127.0.0.1:8001/health
```

Expected response includes `"status":"ok"`.

**Terminal 3 — UI (port 5173)**

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
| 1 | Start reconciliation service | http://127.0.0.1:8002/health |
| 2 | Start backend API | http://127.0.0.1:8001/health |
| 3 | Start UI | http://localhost:5173 |
| 4 | Open the app | http://localhost:5173 |

Keep both terminals open while working. Press `Ctrl+C` in each terminal to stop.

### Common issues

**`.venv` folder not created**

`pip install` alone does not create a virtual environment. Run this first:

```powershell
python -m venv .venv
```

Or use the setup script: `.\scripts\setup.ps1`

If `python` opens the Microsoft Store instead of running Python, install Python from https://www.python.org/downloads/ and enable **Add python.exe to PATH**, then open a new terminal.

**Port already in use (`10048` on 8001 or 5173)**

Another process is using the port. Close the old terminal or stop the process:

```powershell
netstat -ano | findstr :8001
taskkill /PID <pid> /F
```

**`ModuleNotFoundError: No module named 'agentx'`**

Python cannot find the `src/agentx` package. Fix with **one** of these:

```cmd
REM Option 1 (recommended, one-time) — install package into .venv
.\.venv\Scripts\python.exe -m pip install -e .

REM Option 2 — set PYTHONPATH each time before uvicorn (CMD)
set PYTHONPATH=src
```

```powershell
# Option 2 — set PYTHONPATH each time before uvicorn (PowerShell)
$env:PYTHONPATH = "src"
```

**UI loads but API calls fail**

Confirm the backend is running:

```cmd
curl http://127.0.0.1:8001/health
```

## Architecture

- **Backend:** `src/agentx/` — FastAPI, LangGraph pipeline, AnalyticsService, OpsAssistantAgent
- **Reconciliation service:** `src/recon_service/` — separate API that validates ingested vs external-system records
- **Frontend:** `agentx-ui/` — Lit 3 + TypeScript + Vite
- **Seed data:** `seed/demo_data.json` → SQLite on startup

## API

- `GET /api/v1/dashboard/*` — KPIs, journey health, channels
- `GET /api/v1/instructions`, `/exceptions`, `/workbench/requests`
- `POST /api/v1/ingest` — trigger pipeline
- `POST /api/v1/assistant/chat` — SSE chat
- `WS /api/v1/ws/ops` — live updates
