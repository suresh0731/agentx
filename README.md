# AgentX — AI-Powered STP Platform

AgentX is an intelligent straight-through processing (STP) platform for fund operations. It ingests investment instructions from multiple channels, processes them through an AI agent pipeline, routes them to the correct downstream systems, and gives operations teams a single place to monitor performance, handle exceptions, and approve items that need human review.

This document is intended for **business users, reviewers, and demo audiences** — what the solution does, how to launch it, and how to navigate the platform.

---

## Solution Overview

AgentX automates the end-to-end lifecycle of fund instructions — from raw intake (PDF, SWIFT, Excel, API, email, portal uploads) through validation, repair, routing, and reconciliation — while keeping humans in the loop when confidence is low or exceptions arise.

| Capability | Description |
|------------|-------------|
| **Multi-channel ingestion** | Accepts instructions via SWIFT, Email+PDF, API/JSON, Excel templates, and portal file uploads |
| **AI agent pipeline** | Six-stage automated journey: Ingest → Detect → Validate → Repair → Route → Reconcile |
| **98% confidence gate** | Instructions below the confidence threshold are held for human review before auto-creation |
| **Operations Workbench** | Kanban-style queue for submitted, AI-validated, human review, approved, rejected, and escalated items |
| **Exception management** | Prioritised list of instructions that failed or stalled, with inline journey progress |
| **Audit & evidence trail** | Immutable record of every stage, agent decision, and human correction |
| **Operations Command Center** | Real-time KPIs — STP rate, SLA compliance, channel performance, routing distribution |
| **Ops Assistant** | Conversational AI helper for SLA status, reconciliation exceptions, bottlenecks, and priority items |
| **Reconciliation validation** | Cross-checks processed instructions against external settlement records |

### Supported transaction intents

- Subscription
- Redemption
- Switch
- Transfer

### Routing destinations

Processed instructions are dispatched to one of three downstream systems:

- **TA** — Transfer Agent
- **FA** — Fund Accounting
- **IS** — Investor Servicing

---

## Processing Pipeline

Every instruction follows the same six-stage STP journey. The platform tracks progress through each stage in real time.

```
┌──────────┐   ┌────────┐   ┌──────────┐   ┌────────┐   ┌───────┐   ┌───────────┐
│ 1.Ingest │ → │ 2.Detect│ → │3.Validate│ → │4.Repair│ → │5.Route│ → │6.Reconcile│
└──────────┘   └────────┘   └──────────┘   └────────┘   └───────┘   └───────────┘
```

| Stage | What happens |
|-------|--------------|
| **1. Ingestion** | Raw document or message is parsed, localised to English, and normalised into a standard intake format |
| **2. Detect & Classify** | Transaction intent, fund, and key parties are identified |
| **3. Validate & Enrich** | Fields are validated against fund/custody/AML reference data and enriched where possible |
| **4. Repair + Templatise** | Low-confidence or missing fields are auto-repaired; items below **98% confidence** are held for review |
| **5. Routing** | Instruction is dispatched to the correct destination (TA, FA, or IS) |
| **6. Reconciliation** | Settlement records are matched; mismatches raise reconciliation exceptions |

### Two parallel views of every instruction

| Dimension | Purpose |
|-----------|---------|
| **STP Journey** (6 stages above) | Where the instruction is in automated processing |
| **Workbench Queue** (Submitted → AI Validation → Human Review → Approved / Rejected / Escalated) | Where operations staff need to act |

---

## Platform Walkthrough

Open the application at **http://localhost:5173** after launch (see [Getting Started](#getting-started) below).

### 1. Dashboard — Operations Command Center

The landing page provides a real-time snapshot of platform health:

- **Primary KPIs** — Overall STP rate, SLA compliance, average processing time, instructions processed today
- **Secondary metrics** — Reconciliation match rate, auto-repair success, compliance holds, exception queue depth
- **Journey stage performance** — Pass rate per pipeline stage with bottleneck highlighting
- **Attention required** — High-priority exceptions, SLA-at-risk items, reconciliation mismatches, AML holds
- **Channel performance** — Volume and STP rate by intake channel (SWIFT, PDF, Email, Portal, API, Excel)
- **Routing distribution** — Split across TA, FA, and IS
- **STP by intent** — Performance broken down by Subscription, Redemption, Switch, Transfer

Use the **Processing Pipeline Reference** panel at the bottom of the dashboard to expand a visual summary of the six-stage flow.

### 2. Transaction Queue

A live table of all instructions across every intake channel. Each row shows:

- Instruction ID, source file, channel, intent, and destination
- Overall confidence score (colour-coded: green ≥ 98%, amber ≥ 90%, red below 90%)
- Current status and a visual step tracker for the six-stage journey

Click any row to open the **Transaction Detail** modal with full field-level confidence heatmap, evidence timeline, and correction options where applicable.

### 3. Exceptions

A prioritised list of instructions requiring human attention. Each entry shows the issue, where processing stopped in the journey, and priority level. Click a row to inspect the full transaction detail.

### 4. Operations Workbench

The human-in-the-loop control centre, organised as a **Kanban board** with six columns:

| Column | Meaning |
|--------|---------|
| Submitted | Newly received, awaiting AI processing |
| AI Validation | Being processed by the agent pipeline |
| Human Review | Held below confidence gate or flagged for review |
| Approved | Human-approved; journey continues automatically |
| Rejected | Declined by operations |
| Escalated | Escalated for senior review |

**Key actions:**

- **Drag and drop** cards between columns to update workbench stage
- **Click a card** to open the **Review Workspace** — edit fields, view confidence heatmap, add review notes, and approve or reject
- **Insights drawer** — AI-generated operational insights for the current queue
- **Filters** — Narrow by intent or view (all / review only / exceptions only)
- **SLA countdown** — Live SLA remaining on each card

When you approve an item in Human Review, the agent pipeline resumes from its checkpoint and the instruction continues through Route and Reconcile.

### 5. Audit & Evidence Trail

An append-only log of every significant event across all instructions — agent decisions, stage completions, human corrections, and approvals. Each entry records the instruction ID, summary, actor (agent or user), and timestamp.

### 6. Configuration

Displays the active validation rules and repair/templatisation rules applied by AgentX during processing. Useful for understanding what checks run automatically before human review is triggered.

### Ops Assistant

Click **Assistant** in the top navigation bar to open the conversational panel. The assistant can answer operational questions using live platform data, such as:

- *"What's our SLA compliance today?"*
- *"Show reconciliation exceptions"*
- *"List high priority exceptions"*
- *"Which stage is the bottleneck?"*

Suggested queries are shown as quick-action cards when the panel opens.

---

## Getting Started

### Prerequisites

- **Windows** (PowerShell)
- **Python 3.11+** — [python.org/downloads](https://www.python.org/downloads/) (enable *Add python.exe to PATH*)
- **Node.js 18+** — for the web UI

### Launch the platform

From the project root:

```powershell
# First time only — creates virtual environment and installs dependencies
.\scripts\setup.ps1

# Start backend API, reconciliation service, and UI
.\scripts\start-local.ps1
```

Alternatively, double-click `setup.bat` then `start-local.bat`.

Once started, open **http://localhost:5173** in your browser.

| Service | URL | Purpose |
|---------|-----|---------|
| Web UI | http://localhost:5173 | Main application |
| Backend API | http://127.0.0.1:8001/health | Core platform and agent pipeline |
| Reconciliation service | http://127.0.0.1:8002/health | External record validation |

Keep the console windows open while using the platform. Press `Ctrl+C` in each window to stop.

---

## Demo Walkthrough

The platform ships with pre-seeded demo data so you can explore immediately after launch. No additional setup is required for a first walkthrough.

### Suggested review path

1. **Dashboard** — Review KPIs, journey health, and the Attention Required panel. Note the 98% confidence gate callout in the pipeline reference.
2. **Transaction Queue** — Browse live instructions. Click one to see the transaction detail modal with field confidence heatmap and evidence timeline.
3. **Exceptions** — See which instructions stalled and at which pipeline stage.
4. **Operations Workbench** — Open a card in *Human Review*. Correct a field if needed, add a note, and **Approve** to watch the journey continue.
5. **Audit & Evidence** — Confirm the approval and any corrections appear in the immutable trail.
6. **Assistant** — Ask *"Which stage is the bottleneck?"* or use a suggested query card.

### Ingesting new instructions (folder drop)

AgentX watches a local folder for new files and processes them automatically:

| Folder | Purpose |
|--------|---------|
| `data/incoming/` | Drop files here to trigger ingestion |
| `data/processed/` | Successfully completed instructions |
| `data/review/` | Instructions held for human review |
| `data/failed/` | Instructions that failed processing |

Supported file types:

| Extension | Channel |
|-----------|---------|
| `.pdf` | PDF / IDP extraction |
| `.json` | API / client template |
| `.xlsx`, `.xls` | Excel (RTAS) |
| `.swift`, `.mt` | SWIFT (RFAS / SSTM) |
| `.eml`, `.msg` | Email body extraction |

Copy a sample file into `data/incoming/` and watch it appear in the Transaction Queue and Workbench within a few seconds.

### Routed output

Instructions routed to downstream systems produce Excel output in the `routed/` folder (subfolders: RTAS, ViTAL, RFAS depending on destination).

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────┐
│                     AgentX Web UI (port 5173)                    │
│  Dashboard │ Queue │ Exceptions │ Workbench │ Audit │ Config    │
│                        + Ops Assistant panel                     │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST + WebSocket (live updates)
┌────────────────────────────▼────────────────────────────────────┐
│                   AgentX Backend API (port 8001)                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              LangGraph Agent Pipeline                       │  │
│  │  Ingest → Detect → Validate → Repair → Route → Reconcile │  │
│  └──────────────────────────────────────────────────────────┘  │
│  Analytics Service │ Ops Assistant Agent │ Folder Poller         │
└────────────┬───────────────────────────────┬─────────────────────┘
             │                               │
┌────────────▼────────────┐    ┌─────────────▼─────────────────────┐
│  SQLite (in-memory demo) │    │  Reconciliation Service (8002)  │
│  Seeded + live pipeline  │    │  Validates vs external records  │
└─────────────────────────┘    └──────────────────────────────────┘
```

**Key design points for reviewers:**

- All operational data (instructions, metrics, audit events) lives in the backend database, seeded on startup and updated live as the pipeline runs.
- The UI reflects real API data — no hardcoded metrics or transaction rows in the frontend.
- WebSocket connections push live updates to the queue, workbench, and exception views as instructions progress.
- Human approvals resume the agent pipeline from a checkpoint — no re-processing from scratch.

---

## Glossary

| Term | Definition |
|------|------------|
| **STP** | Straight-Through Processing — fully automated end-to-end handling without manual intervention |
| **Instruction** | A single fund transaction request (subscription, redemption, switch, or transfer) |
| **Confidence gate** | Minimum field-confidence threshold (98%) required for automatic creation without human review |
| **Golden schema** | Normalised transaction format all agents converge on |
| **HITL** | Human-in-the-Loop — operations review and approval when automation cannot proceed confidently |
| **Intake JSON** | Standardised output of the ingestion stage, feeding all downstream agents |
