
# Submission Summary — BrainFlow AI

## Problem it solves

Small and medium delivery businesses react to operational problems after they happen. BrainFlow AI is a bounded operations console that helps an operator monitor → detect → analyze → optimize → simulate → approve → execute → evaluate on synthetic demonstration data. The full loop works end-to-end.

## Key capabilities

- Deterministic risk engine — 0–100 score, 5 documented factors, confidence, category. Reproducible.
- Exception center — stable-identity deduplication across scans, auto-resolve/reopen.
- Recovery planner — documented objective, feasibility repair pass, three alternatives (baseline / minimize_delays / balanced). Deterministic, tested.
- Isolated simulator — baseline / no-recovery / recovered triple on snapshots. Never mutates DB.
- Human approval + execution — DRAFT → PENDING → APPROVED → EXECUTED, idempotent, stale-plan rejection on revalidation failure.
- Bounded AI copilot — answers built from DB; LLM only rephrases prose. Deterministic fallback when no key.
- Append-only audit trail — every consequential action recorded.
- Single-admin login — bcrypt password, server-side sessions, HttpOnly cookie.
- Background scans — APScheduler every 5 min, no overlap, disableable.

## Architecture

Frontend — React 19, TS 5.8 strict, Vite 8, Tailwind 3, shadcn-style (Radix + CVA), TanStack Query, React Router, Recharts, RHF + Zod, Sonner.

Backend — FastAPI, Pydantic v2, SQLAlchemy 2.1, Alembic (7 migrations), SQLite default with Postgres path, APScheduler, httpx, passlib[bcrypt].

AI — Gemini via google-genai, provider abstraction with deterministic fallback.

External — Open-Meteo, Nager.Date, both cached and fallback-safe.

See docs/ARCHITECTURE.md and docs/TECHNICAL_DECISIONS.md.

## Tests executed

| Suite | Command | Result |
|---|---|---|
| Backend | `pytest -q` | 73 passed |
| Frontend | `npm run test` | 16 passed (6 files) |
| Type check | `npx tsc --noEmit -p tsconfig.app.json` | 0 errors |
| Build | `npm run build` | success |
| Lint | `npm run lint` | 0 errors, 3 informational warnings |
| Prod deps audit | `npm audit --omit=dev` | 0 vulnerabilities |

Full breakdown in docs/TESTING.md.

## How to run and demo

Run:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd .. && cp .env.example .env
cd backend && alembic upgrade head && python -m scripts.seed
uvicorn app.main:app --reload --port 8000 --log-config uvicorn.log_config.json

# new terminal
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Login: admin / BrainFlow@2026.

Demo: docs/DEMO_GUIDE.md — 15-minute walkthrough (login → scan → exceptions → recovery → approve → execute → audit → simulations → copilot → analytics).

## Environment variables

See .env.example. Key: ADMIN_USERNAME/PASSWORD, SESSION_TTL_HOURS, SCHEDULER_ENABLED, SCAN_INTERVAL_MINUTES, DATABASE_URL, GEMINI_API_KEY, CORS_ORIGINS, COOKIE_SECURE.

## Limitations

Full list in docs/KNOWN_LIMITATIONS.md. Highlights:

- Demonstration data only — no real logistics integrations
- Rule-based risk (not trained ML)
- Greedy planner (not optimal)
- Single admin, no RBAC
- No CSRF token (SameSite=Lax + POST-only + CORS)
- APScheduler in-process (single-worker)
- Single ~1 MB frontend bundle — route split is a follow-up
- Playwright E2E optional

## Submission package

```
brainflow-ai/
├── README.md
├── SUBMISSION_SUMMARY.md     ← this file
├── .env.example
├── docs/
│   ├── ARCHITECTURE.md
│   ├── TECHNICAL_DECISIONS.md
│   ├── TESTING.md
│   ├── DEMO_GUIDE.md
│   └── KNOWN_LIMITATIONS.md
├── backend/                  ← FastAPI, 73 tests
└── frontend/                 ← React 19, 16 tests
```

Repository: github.com/firatolin/brainflow-ai

## Suggested message to Kidus

Hi Kidus,

BrainFlow AI is ready for review: github.com/firatolin/brainflow-ai

A full-stack logistics operations platform with a deterministic risk engine, exception center, recovery planner, what-if simulator, human-approval workflow with stale-plan rejection and idempotent execution, bounded AI copilot with deterministic fallback, and an append-only audit trail. Working end-to-end on synthetic demo data.

Highlights:

- 73 backend tests + 16 frontend tests, all passing
- Type check, lint, and production build all green
- Runs on pytest, npm run test, npm run build with zero external services
- AI and external APIs are optional — the app works fully offline via deterministic fallbacks

Start with README.md, then docs/DEMO_GUIDE.md for a 15-minute walkthrough. Known limitations are honestly documented in docs/KNOWN_LIMITATIONS.md.

Thank you — happy to walk through anything during the review.
