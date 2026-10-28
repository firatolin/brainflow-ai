
# Testing

All commands below were executed and their results recorded in this session.

## Summary

| Suite | Command | Result |
|---|---|---|
| Backend | `pytest -q` | 73 passed |
| Frontend | `npm run test` | 16 passed (6 files) |
| Type check | `npx tsc --noEmit -p tsconfig.app.json` | 0 errors |
| Build | `npm run build` | success |
| Lint | `npm run lint` | 0 errors, 3 informational warnings |
| Prod deps audit | `npm audit --omit=dev` | 0 vulnerabilities |

## Backend (73 tests)

`tests/` — health, deliveries (CRUD + state machine + capacity + history), vehicles, risk engine (determinism, monotonicity, factors), incidents (dedup, auto-resolve), scan runs, planner (feasibility repair, determinism), plans API, simulator (isolation), approval flow (idempotent execution, stale-plan rejection), audit, copilot (routing + fallback), customer drafts (template fallback), auth (login/logout/mutation guards), context (weather/holidays), dashboard, analytics, settings.

Isolation: fresh in-memory SQLite per test via StaticPool. Scheduler not started. No external API called. Admin user created per test DB; TestClient auto-logs in unless `@pytest.mark.no_auth`.

## Frontend (16 tests, 6 files)

`src/lib/__tests__/utils.test.ts`, `src/components/overview/__tests__/KpiCard.test.tsx`, `src/components/shared/__tests__/StatusBadge.test.tsx`, `src/pages/__tests__/LoginPage.test.tsx`, `src/pages/__tests__/OverviewPage.test.tsx`, `src/pages/__tests__/DeliveriesPage.test.tsx`.

All fetch mocked per test.

## Not tested automatically

- Visual styling (text/behavior only)
- Real Gemini provider (fallback path only)
- Live Open-Meteo/Nager.Date responses
- APScheduler firing — verified manually during development: `Scheduled scan ok id=3 scanned=40 new_incidents=0 auto_resolved=0 duration_ms=89` fired every interval without overlap.
