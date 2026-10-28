# BrainFlow AI

**AI-powered logistics operations platform** — detect disruptions, predict delivery risks, evaluate recovery plans, simulate alternatives, and coordinate actions with human oversight.

> **This is a demonstration application.** All data, deliveries, vehicles, and outcomes are synthetic and clearly labelled as demonstration data. There are no real external logistics integrations, and nothing is sent to real customers.

---

## Problem it solves

Small and medium-sized delivery businesses typically react to operational problems after they happen: a delivery goes late, a vehicle breaks down, a storm delays several routes. Managers have to reconstruct the whole day's state manually and guess what to do next.

BrainFlow AI turns this into a bounded operational console:

- **Monitor** deliveries and fleet in real time
- **Detect** disruptions with a deterministic risk engine and an exception center
- **Analyze** the current state through dashboards and a bounded AI copilot
- **Optimize** recovery using a documented, deterministic planner
- **Simulate** alternative decisions without touching production state
- **Approve** operational changes through a human-in-the-loop workflow
- **Execute** approved actions with revalidation and full audit trail
- **Evaluate** outcomes with analytics over persisted data

The workflow is always **Monitor → Detect → Analyze → Optimize → Simulate → Approve → Execute → Evaluate**.

---

## Highlights

- **Rule-based risk engine** (0–100 score, factor breakdown, confidence) — deterministic, testable, reproducible
- **Exception center** with **stable identity deduplication** across scans, automatic resolve/reopen
- **Recovery planner** with a documented objective function and a **feasibility repair pass** for pre-existing violations
- **What-if simulator** that operates on isolated snapshots — **never mutates production state**
- **Human approval workflow** with idempotent execution, stale-plan rejection, and append-only audit trail
- **Bounded AI copilot** — answers are built from backend data; the LLM is only allowed to rephrase prose, never invent facts
- **Deterministic fallbacks** for LLM, weather, and holidays — the app works fully offline
- **Single-admin login** with bcrypt-hashed password and server-side session cookies
- **Background scans** every 5 minutes with no overlap, disableable in tests

---

## Architecture

    ┌──────────────────────────────┐     ┌──────────────────────────────┐
    │ Frontend (Vite + React + TS) │ /api│ Backend (FastAPI + Python)   │
    │ - Router + TanStack Query    │◀───▶│ - REST + SQLAlchemy          │
    │ - Tailwind + shadcn-style    │proxy│ - APScheduler background     │
    │ - Recharts                   │     │ - Deterministic services     │
    └──────────────────────────────┘     │ - Gemini provider fallback   │
                                         │ - Open-Meteo, Nager.Date     │
                                         └──────────┬───────────────────┘
                                                    │
                                                    ▼
                                         ┌──────────────────────────────┐
                                         │ SQLite (default)             │
                                         │ PostgreSQL-ready             │
                                         └──────────────────────────────┘

Full details: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Technology stack

**Frontend** — React 19, TypeScript 5.8 (strict), Vite 8, Tailwind CSS 3, shadcn-style primitives (Radix + CVA), TanStack Query, React Router, Recharts, Lucide, React Hook Form + Zod, Sonner (toasts), date-fns, Vitest + React Testing Library.

**Backend** — Python 3.12+ (tested on 3.14), FastAPI, Pydantic v2, SQLAlchemy 2.1, Alembic, SQLite (default), APScheduler, httpx, pytest, passlib[bcrypt].

**AI** — Gemini via `google-genai` (optional). **Provider abstraction** — if `GEMINI_API_KEY` is empty, a deterministic fallback provider is used and every response is labelled `source: "fallback"`.

**External** — Open-Meteo (weather, cached, timeout, demo fallback), Nager.Date (holidays, cached, demo fallback).

---

## Project structure

    brainflow-ai/
    ├── backend/
    │   ├── app/
    │   │   ├── api/          # FastAPI routers
    │   │   ├── core/         # config, DB, auth dependency, deps
    │   │   ├── integrations/ # LLM, weather, holidays clients
    │   │   ├── models/       # SQLAlchemy ORM (14 tables)
    │   │   ├── schemas/      # Pydantic v2
    │   │   └── services/     # risk, incidents, planner, simulator, approvals, audit, …
    │   ├── alembic/          # migrations
    │   ├── scripts/seed.py   # deterministic seed + admin creation
    │   ├── tests/            # pytest (73 tests)
    │   ├── requirements.txt
    │   ├── uvicorn.log_config.json
    │   └── pytest.ini
    ├── frontend/
    │   ├── src/
    │   │   ├── api/          # typed endpoints + client
    │   │   ├── components/   # ui, layout, shared, overview
    │   │   ├── hooks/        # useAuth, useHealth, useDashboard
    │   │   ├── pages/        # 11 routed pages
    │   │   └── test/         # vitest setup + helpers
    │   ├── vitest.config.ts
    │   ├── vite.config.ts
    │   └── package.json
    ├── docs/
    │   ├── ARCHITECTURE.md
    │   ├── TECHNICAL_DECISIONS.md
    │   ├── TESTING.md
    │   ├── DEMO_GUIDE.md
    │   └── KNOWN_LIMITATIONS.md
    ├── SUBMISSION_SUMMARY.md
    ├── .env.example
    └── README.md

---

## Prerequisites

- **Node.js** ≥ 20 (tested on 24.20)
- **Python** ≥ 3.12 (tested on 3.14) — if wheels are missing on newer Python, use 3.12
- SQLite (bundled with Python)

---

## Installation

```bash
# 1) Clone and enter
git clone <repo-url> brainflow-ai
cd brainflow-ai

# 2) Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3) Configure environment
cd ..
cp .env.example .env
#    Edit .env if you want to change the admin password, CORS, or add GEMINI_API_KEY

# 4) Migrate + seed
cd backend
alembic upgrade head
python -m scripts.seed

# 5) Frontend
cd ../frontend
npm install
```

## Running

Open two terminals.

**Terminal 1 — backend**

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000 --log-config uvicorn.log_config.json
```

Backend is at http://127.0.0.1:8000. Interactive API docs at http://127.0.0.1:8000/docs.

**Terminal 2 — frontend**

```bash
cd frontend
npm run dev
```

Open http://localhost:5173.

### Login (seeded admin)

| Field    | Value          |
|----------|----------------|
| Username | admin          |
| Password | BrainFlow@2026 |

Change `ADMIN_PASSWORD` in `.env` and re-run `python -m scripts.seed` (with the DB deleted) if you want different credentials.

## Environment variables

See `.env.example`. Key ones:

| Variable | Default | Purpose |
|---|---|---|
| `APP_ENV` | development | Environment label |
| `CORS_ORIGINS` | http://localhost:5173,... | Allowed frontend origins |
| `DATABASE_URL` | SQLite file | Swap to `postgresql+psycopg://...` for Postgres |
| `ADMIN_USERNAME` / `ADMIN_DISPLAY_NAME` / `ADMIN_PASSWORD` | admin / Admin / BrainFlow@2026 | Seeded admin |
| `SESSION_TTL_HOURS` | 8 | Session cookie lifetime |
| `COOKIE_SECURE` | false | Set true in production HTTPS |
| `SCHEDULER_ENABLED` | true | Background scans |
| `SCAN_INTERVAL_MINUTES` | 5 | Scan frequency |
| `GEMINI_API_KEY` | (empty) | Leave blank for deterministic fallback |
| `GEMINI_MODEL` | gemini-2.0-flash | Gemini model name |
| `PUBLIC_HOLIDAY_COUNTRY` | ET | Nager.Date country code |

## Database

SQLite file at `backend/brainflow.db` by default. Reset:

```bash
cd backend
rm -f brainflow.db
alembic upgrade head
python -m scripts.seed
```

PostgreSQL path: set `DATABASE_URL=postgresql+psycopg://...` in `.env`, install `psycopg[binary]`, then run the same migration + seed commands.

Migrations — 6 Alembic revisions:

1. initial: deliveries and vehicles
2. add delivery_history
3. add risk_assessments, incidents, scan_runs
4. add recovery plans and simulations
5. add operational actions, approvals, audit events
6. add users and sessions

## Seed data

`python -m scripts.seed` creates:

- 6 vehicles — VAN-01 (central, 8), VAN-02 (north, 8), TRK-01 (south, 20), MBK-01 (central, 2), VAN-03 (unavailable — maintenance), CAR-01 (airport, 4)
- 43 deliveries — 2 urgent + 38 normal + 3 delivered
- The scenario is built-in: MBK-01 gets 4 active deliveries (capacity 2 — triggers a capacity_exceeded incident and exercises the planner's repair pass), 2 urgent deliveries (one unassigned), heavy rain exposure on several deliveries
- 1 admin user from `.env` credentials

The seed is deterministic (`random.Random(42)`) and idempotent when re-run with `reset=True` (the default — wipes workflow tables).

## Tests

```bash
# Backend
cd backend && source .venv/bin/activate && pytest -q
# → 73 passed

# Frontend
cd frontend && npm run test
# → Test Files 6 passed, Tests 16 passed

# Type check + build
npx tsc --noEmit -p tsconfig.app.json
npm run build
```

See `docs/TESTING.md` for coverage details and what is not tested automatically.

## AI provider (optional)

The app works fully without an AI key. When `GEMINI_API_KEY` is set:

- The `/api/copilot/query` endpoint uses Gemini to rephrase a deterministic answer. The facts are always built from the database. The LLM cannot invent delivery IDs, vehicle codes, or operational values.
- The `/api/customer-drafts/{id}` endpoint uses Gemini to polish a template message. The template is the fallback.

When the key is missing:

- `/api/health` reports `ai: { provider: "fallback", configured: false }`
- Copilot answers include a note: "AI rephrasing is disabled — GEMINI_API_KEY is not set."
- Customer drafts are returned with `source: "template"`

Never commit a real key. `.env` is gitignored.

## External integrations

| Service | Purpose | Endpoint | Fallback |
|---|---|---|---|
| Open-Meteo | Weather context | `GET /api/context/weather?zone=…` | Deterministic demo values |
| Nager.Date | Public holidays | `GET /api/context/holidays?country=…` | Empty list |

Both are cached in-memory (10 min for weather, 6 h for holidays) and use httpx with `EXTERNAL_TIMEOUT_SECONDS` timeout. The app never fails because an external service is down.

## Demonstration workflow

See `docs/DEMO_GUIDE.md` for the full 15-minute script. Short version:

1. Seed — `python -m scripts.seed`
2. Login — admin / BrainFlow@2026
3. Run scan — topbar button. KPIs update; open incidents rise
4. Exceptions — incidents grouped by severity. Acknowledge one. Resolve one
5. Recovery — Generate plans. Three cards appear (baseline, minimize_delays, balanced). Compare metrics
6. Submit for approval — pick the feasible plan
7. Approvals — Approve → Execute. `execution_result` shows applied changes
8. Audit — search the trail. Every step is recorded
9. Simulations — run a "vehicle unavailable" scenario. Compare baseline vs simulated vs recovered
10. Copilot — ask "Which deliveries are most likely to be late?" — answer is deterministic (or LLM-enhanced if configured)
11. Analytics — 14-day trends, incident breakdown, vehicle utilization, plan comparison

Every consequential change went through Detect → Plan → Simulate → Approve → Execute.

## Security

This is a single-operator demo. Known scope:

- ✅ Environment-based secrets — no keys in frontend or code
- ✅ Bcrypt-hashed passwords (passlib)
- ✅ HttpOnly, SameSite=Lax server-side session cookies (hashed at rest)
- ✅ All mutating endpoints require auth — reads are intentionally public for demo friendliness
- ✅ CORS locked to configured origins
- ✅ Pydantic validation on every input
- ✅ Audit trail is append-only via application interfaces
- ✅ Explicit stale-plan rejection — execution revalidates against current DB state
- ✅ Idempotent execution — double-execute returns the same result without re-applying

Not implemented (documented in `docs/KNOWN_LIMITATIONS.md`):

- CSRF tokens (relies on SameSite=Lax + POST-only mutations + same-origin CORS)
- Multi-user roles / RBAC
- Rate limiting
- Distributed scheduler (APScheduler runs in-process)

Do not deploy this as-is to a public production environment.

## API documentation

- Interactive: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

Key endpoints:

    GET    /api/health
    POST   /api/auth/login | /api/auth/logout
    GET    /api/auth/status
    GET    /api/dashboard/summary
    GET    /api/analytics/summary
    GET    /api/deliveries                (list/filter/sort/paginate)
    POST   /api/deliveries                (auth)
    PATCH  /api/deliveries/{id}           (auth)
    POST   /api/deliveries/{id}/assign    (auth)
    POST   /api/deliveries/{id}/status    (auth)
    GET    /api/vehicles                  (list/filter/paginate)
    POST   /api/vehicles                  (auth)
    PATCH  /api/vehicles/{id}             (auth)
    GET    /api/incidents                 (list/filter)
    POST   /api/incidents/scan            (auth)
    PATCH  /api/incidents/{id}            (auth)
    POST   /api/risk/assess
    POST   /api/plans/generate            (auth)
    GET    /api/plans
    GET    /api/plans/{id}
    POST   /api/plans/{id}/submit         (auth)
    POST   /api/simulations               (auth)
    GET    /api/simulations/{id}
    GET    /api/actions                   (list/filter)
    POST   /api/actions/{id}/approve      (auth)
    POST   /api/actions/{id}/reject       (auth)
    POST   /api/actions/{id}/execute      (auth)
    GET    /api/audit-events              (list/search)
    GET    /api/scan-runs | POST /api/scan-runs
    POST   /api/copilot/query             (auth)
    GET    /api/context/weather | /api/context/holidays
    GET    /api/customer-drafts/{id}
    GET    /api/settings

## Known limitations

Full list in `docs/KNOWN_LIMITATIONS.md`. Highlights:

- Demonstration data only — no real logistics system integration
- Rule-based risk, not trained ML — the description says so
- Single admin user, no RBAC
- No CSRF token (relies on SameSite=Lax)
- APScheduler runs in-process (single worker); not designed for multi-instance deployment
- Frontend bundle is a single 1 MB chunk — route splitting is a follow-up
- Playwright E2E is optional and not part of the default test run

## Screenshots

Capture these while running the app for the submission package:

- `docs/screenshots/01-login.png`
- `docs/screenshots/02-overview.png`
- `docs/screenshots/03-deliveries.png`
- `docs/screenshots/04-exceptions.png`
- `docs/screenshots/05-recovery.png`
- `docs/screenshots/06-approvals.png`
- `docs/screenshots/07-simulation.png`
- `docs/screenshots/08-audit.png`

(You can also embed them here — just add `![Overview](docs/screenshots/02-overview.png)` under a `## Screenshots` header.)

## License / attribution

Assignment submission. Not for production use.
