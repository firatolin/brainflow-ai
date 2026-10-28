# Demo Guide

A 15-minute walkthrough that exercises every core capability of BrainFlow AI end-to-end. **No live backend or external APIs required beyond the two commands below.**

---

## Preparation (2 min)

### Terminal 1 — backend

    cd backend
    source .venv/bin/activate
    alembic upgrade head
    python -m scripts.seed
    uvicorn app.main:app --reload --port 8000 --log-config uvicorn.log_config.json

Wait for:

    brainflow.scheduler: Scheduler started: interval=5min next_run=...
    INFO:     Application startup complete.

### Terminal 2 — frontend

    cd frontend
    npm run dev

Open http://localhost:5173.

### Login

| Field    | Value          |
|----------|----------------|
| Username | admin          |
| Password | BrainFlow@2026 |

You land on Overview.

## Step 1 — Baseline state (1 min)

Look at the Overview page:

- Active deliveries: 40
- At risk: 0 (no scan yet — risk scores are 0 until a scan)
- Delayed: 0
- On-time rate: 0% or —
- Active vehicles: 5
- Open incidents: 0
- Pending approvals: 0
- Delay exposure: 0h

Below the KPIs: 7-day trend (mostly zeros), risk distribution (all low), status distribution (pending/assigned bars), empty recent activity.

Note: Before the first scan, risk scores are 0 because no delivery has been assessed yet. The demo scenario's difficulty is invisible until we scan.

## Step 2 — Run a scan (1 min)

Click **Run scan** in the topbar.

Toast: `Scan complete: 40 scanned, N new, 0 auto-resolved`

- Open incidents rises (18 in the seeded scenario)
- At risk rises (a handful of deliveries)
- Recent activity populates with audit events
- Delay exposure becomes non-zero

What just happened:

- Risk engine ran on every active delivery
- Incidents were detected with deduplication
- A `ScanRun` row recorded the scan
- Scheduler confirmed running (topbar shows "next scan: …")

Open **Exceptions** in the sidebar to see the resulting incidents.

## Step 3 — Explore exceptions (2 min)

On Exceptions, incidents are grouped by severity:

- `unassigned_high_priority` — BF-URG-002 (urgent) has no vehicle
- `capacity_exceeded` — MBK-01 has 4 active deliveries against capacity 2
- `severe_weather` — deliveries with weather exposure ≥ 0.5
- `late_likely` — deliveries whose risk score ≥ 50

Acknowledge the `capacity_exceeded` one → its badge flips to acknowledged.

Resolve a `severe_weather` one → confirmation dialog → badge flips to resolved.

Notice these actions are recorded — you'll find them later in Audit history.

## Step 4 — Recovery planning (3 min)

Open **Recovery planning**.

Click **Generate plans**.

Three cards appear:

- `baseline` — current state, marked infeasible (capacity_exceeded on MBK-01)
- `minimize_delays` — feasible, N changes, lower late count
- `balanced` — feasible, fewer changes, slightly higher delay

Click each card to see:

- Metrics: late deliveries, total delay, priority-weighted delay, extra cost, changes
- Explanation: plain-English summary including "Rule-based heuristic estimate, not a trained prediction"
- Items table: which delivery moves from which vehicle to which

Key insight: the `minimize_delays` plan is feasible because the planner's repair pass fixed the MBK-01 overflow by moving deliveries to vehicles with spare capacity. The current state was infeasible; the plan is not.

Select `minimize_delays` → click **Submit for approval** → confirm.

Toast: *Plan submitted for approval.* The plan status becomes submitted. Go to Approvals.

## Step 5 — Approvals (2 min)

On Approvals (default filter = `pending_approval`):

You see a card with:

- `pending_approval` badge
- Reason: Recovery plan `minimize_delays` with N change(s)
- Expected impact
- Requested timestamp

Click **Approve** → toast. Status becomes approved. Card now shows **Execute** button.

Click **Execute** → toast *Executed — Applied N changes.* Status becomes executed.

Click **Execute** again → no-op (idempotent). No duplicate changes.

Now navigate to **Deliveries** — you'll see deliveries now assigned to different vehicles than at seed time. Click one to see the **History** timeline showing assigned/unassigned/status_changed events.

## Step 6 — Audit trail (1 min)

Open **Audit history**.

You'll see every action from the demo so far:

- `action.submitted` (by Admin)
- `action.approved` (by Admin)
- `delivery.reassigned` × N (by Admin — one per changed delivery)
- `action.executed` (by Admin — exactly once)

Use the **Event type** filter to narrow. Try the search box with `Admin` — every step is attributed.

Note: the audit trail is append-only — this is the ground truth of what happened.

## Step 7 — What-if simulation (2 min)

Open **Simulations**.

Scenario: **Vehicle unavailable**

- Select VAN-01
- Click **Run simulation**

Result panel shows:

- Baseline: late count, delay, feasible
- No recovery: how bad it would get if VAN-01 vanished and nothing else changed
- Recovered: how the planner would fix it
- Deltas: Δ late (no recovery) and Δ late (with recovery)

Key insight: the recovery dramatically reduces the hit. This is a safe preview — nothing was actually changed.

Try also:

- **Heavy rain** with delta 0.5 → total delay increases under the scenario; recovery reduces it
- **Deadline moved earlier** on a delivery → simulated plan has more late deliveries

## Step 8 — Copilot (2 min)

Open **AI Copilot**.

Click *"Which deliveries are most likely to be late?"*

Assistant responds with a numbered list of deliveries, their IDs, risk scores, and priorities.

Look at the badge under the answer:

- If `GEMINI_API_KEY` is not set: **deterministic fallback** + "AI rephrasing is disabled"
- If it is set: **llm**

Try *"Summarize the current operational situation"* and *"What is causing today's largest operational risk?"*

Key insight: the copilot only answers from backend data. It cannot invent delivery IDs.

## Step 9 — Analytics (1 min)

Open **Analytics**.

- Measured: total deliveries, delivered, on-time rate, delay rate, completion rate, avg delay, cost aggregates
- Estimated: risk distribution, vehicle utilization
- Incidents: total, by kind, avg resolution time
- Plan comparison table: latest plans with feasibility, late count, delay, cost, changes
- 14-day trend: delivered vs incidents (line chart)

Notice the labels distinguishing measured outcomes from rule-based estimates.

## Step 10 — Settings (1 min)

Open **Settings**.

- Application: name, env, auth mode (demo_no_auth → but a session-based demo admin)
- Admin account: username, display name, signed-in state
- System status: backend health, database status, AI provider
- External context: weather source (open-meteo or demo), holidays source (nager or 0 entries)

## Step 11 — Background monitoring (30 sec, optional)

The scheduler runs every 5 minutes. You can observe:

    cd backend
    tail -f uvicorn.log

You'll see (approximately every 5 min):

    brainflow.scheduler: Scheduled scan ok id=N scanned=40 new_incidents=0 auto_resolved=0 duration_ms=...

`new_incidents=0` after the first scan is correct — deduplication means repeated scans don't spam.

## What this demo proves

| Requirement | Where shown |
|---|---|
| Real full-stack app | Login → Overview → everything |
| Real DB persistence | Deliveries change after plan execution |
| Business logic | Risk engine, incident detection, planner |
| End-to-end workflow | Scan → Plan → Approve → Execute → Audit |
| Auto-generated tests | 73 backend + 16 frontend |
| Deterministic fallbacks | Copilot + weather without external services |
| Human approval mandatory | Approvals gate before execution |
| Stale-plan protection | (Try drift mid-flow — 409 response) |
| Audit trail | Full event history |
| Background monitoring | APScheduler logs |
| Rule-based decisions | Explicitly labelled |

## Reset the demo

    cd backend
    rm -f brainflow.db
    alembic upgrade head
    python -m scripts.seed

The database is rebuilt from migrations + deterministic seed. All data returns to the initial state. Restart uvicorn if it's running.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Login fails | Confirm `ADMIN_PASSWORD=BrainFlow@2026` in `.env`; if you changed it after seeding, reset the DB |
| Weather/holidays show demo | Network offline or Nager/Open-Meteo unreachable — expected |
| Scan failed: Not authenticated | Session cookie expired — sign in again |
| Empty pages | Confirm the backend is running on port 8000 (`curl http://127.0.0.1:8000/api/health`) |
| CORS error | Set `CORS_ORIGINS` in `.env` to include your frontend origin |
| Scheduler logs silent | `SCHEDULER_ENABLED=true` in `.env` and log config used (`--log-config uvicorn.log_config.json`) |
