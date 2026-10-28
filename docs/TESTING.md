# Testing

Coverage details, how to run, and what is **not** tested automatically in BrainFlow AI.

---

## How to run

### Backend

```bash
cd backend
source .venv/bin/activate
pytest -q                 # all tests, quiet
pytest -v                 # verbose
pytest tests/test_risk_engine.py   # single file
pytest -k "idempotent"    # by name
```

Expected: `73 passed`.

### Frontend

```bash
cd frontend
npm run test              # vitest, watch mode off (CI)
npm run test -- --watch   # watch
npm run lint              # eslint
npx tsc --noEmit -p tsconfig.app.json   # type check
npm run build             # production build
```

Expected: `Test Files 6 passed, Tests 16 passed`.

---

## Backend test infrastructure

- `pytest` with in-memory SQLite per test (`StaticPool` so all sessions share one connection)
- No live external APIs — weather/holidays/LLM all fall back deterministically
- `TestClient` with dependency override for the DB session
- Auto-login fixture: tests are authenticated as `admin` unless marked `@pytest.mark.no_auth`
- Admin user seeded via `auth_service.ensure_admin_user` in the fixture
- `pytest.ini` configures test paths and markers

---

## Backend coverage (73 tests)

| File | Tests | Focus |
|---|---|---|
| `test_risk_engine.py` | 6 | Score formula, category boundaries, confidence, determinism |
| `test_incidents.py` | 5 | Detection kinds, dedup across scans, auto-resolve, reopen |
| `test_planner.py` | 7 | Baseline no-op, capacity respect, repair pass, determinism, 3 plans, objective |
| `test_simulator.py` | 6 | Snapshot isolation, no DB mutation, baseline/no-recovery/recovered triple |
| `test_approval_flow.py` | 6 | Submit → approve → execute, requires approval, idempotency, stale rejection |
| `test_audit.py` | 1 | Audit event recording on execution |
| `test_auth.py` | 7 | Login success/failure, status, logout, cookie, mutation gating |
| `test_deliveries.py` | 8 | List/filter/sort/paginate, create, assign, status, history |
| `test_vehicles.py` | 4 | List/filter/paginate, create, edit |
| `test_plans_api.py` | 3 | Generate, get, submit |
| `test_scan_runs.py` | 3 | Run scan, list, persistence |
| `test_dashboard.py` | 3 | Summary KPIs, trends |
| `test_analytics.py` | 3 | Aggregates, incident breakdown, plan comparison |
| `test_copilot.py` | 4 | Deterministic routing, fallback note, no invented IDs |
| `test_customer_drafts.py` | 2 | Template fallback, `source: "template"` |
| `test_context.py` | 3 | Weather + holidays, demo fallback |
| `test_settings.py` | 1 | Settings endpoint shape |
| `test_health.py` | 1 | Health payload including AI provider |

---

## Frontend coverage (16 tests, 6 files)

| File | Tests | Focus |
|---|---|---|
| `src/components/overview/__tests__/KpiCard.test.tsx` | 3 | KPI rendering, formatting |
| `src/components/shared/__tests__/StatusBadge.test.tsx` | 4 | Badge variant mapping |
| `src/lib/__tests__/utils.test.ts` | 2 | `cn` merge utility |
| `src/pages/__tests__/OverviewPage.test.tsx` | 2 | KPI numbers from dashboard data |
| `src/pages/__tests__/DeliveriesPage.test.tsx` | 2 | Table render, total count |
| `src/pages/__tests__/LoginPage.test.tsx` | 3 | Form fields, validation, submit |

Frontend tests use Vitest + React Testing Library with a mocked `fetch` (`src/test/mockFetch.ts`). No real backend is required.

---

## What is tested (highlights)

- Risk score formula and category thresholds
- Incident deduplication across repeated scans
- Auto-resolve / auto-reopen of incidents
- Planner determinism and capacity enforcement
- Planner feasibility repair on pre-existing violations
- Simulation never mutates DB rows (asserted)
- Approval lifecycle: submit → approve → execute
- Execution requires approval; rejection blocks execution
- Execution is idempotent (second call is a no-op)
- Stale-plan rejection on DB drift
- Audit trail records every consequential step
- Auth: login, logout, status, mutation gating, `no_auth` marker
- Copilot deterministic fallback when no API key
- Customer drafts `source: "template"` fallback
- Weather/holidays demo fallback
- Dashboard and analytics aggregates

---

## What is NOT tested automatically

- **Real Gemini provider** — only the fallback path is verified. The LLM polish path is exercised manually.
- **Live Open-Meteo / Nager.Date responses** — only the fallback path is verified.
- **Scheduler timing** — APScheduler is disabled in tests to avoid flaky timing; verified manually.
- **Playwright E2E** — the full demo workflow is exercised manually per `docs/DEMO_GUIDE.md`.
- **PostgreSQL path** — only SQLite is exercised in CI.
- **Performance / load** — not applicable for a demo.
- **Accessibility (axe-core)** — semantic HTML used but not asserted.
- **Visual regression** — none.
- **Full coverage of all 11 pages** — only Overview, Deliveries, Login are tested.
- **Dark mode / responsive layouts** — not tested (no dark mode exposed).

---

## Lint and type checks

- `npm run lint` → **0 errors, 3 informational warnings** (`react-hooks/incompatible-library` for React Hook Form `watch()`).
- `npx tsc --noEmit -p tsconfig.app.json` → **0 errors**.
- `npm audit --omit=dev` → **0 vulnerabilities**.
