# Known Limitations

Honest list of what this demo build does **not** do, and why. All decisions are documented so a reviewer can judge scope clearly.

---

## Scope and data

- **Demonstration data only.** All deliveries, vehicles, customers, and outcomes are synthetic. The seed script generates ~43 deliveries and 6 vehicles deterministically.
- **No real external logistics integrations.** No carrier API, no live GPS, no real customer notifications. Customer messages are **drafts only**, never sent.
- **No real payments, invoicing, or financial systems.**
- **No historical dataset** — risk scores are a rule-based estimate, **not a trained ML model**.

---

## Risk engine

- **Rule-based, not statistically trained.** The formula is documented in `docs/ARCHITECTURE.md` and the code. It is deterministic and reproducible.
- **The confidence value is a heuristic**, not a statistical confidence interval.
- **Average speed is a fixed assumption** (25 km/h) used to estimate travel time from distance. A real system would use routing APIs or historical driving data.

---

## Optimizer / planner

- **Greedy heuristic, not optimal.** We explicitly do not claim to solve a VRP. The planner is a local-improvement algorithm with a feasibility repair pass.
- **No vehicle sequencing model.** The planner changes assignments but does not compute per-vehicle delivery order.
- **No multi-depot, multi-shift, or time-window models.**
- **Assumed distances and costs** are taken from the seed data, not from external routing.

---

## Simulations

- **Estimate only.** The simulator computes delay using the same travel-time model as the risk engine. Real outcomes would vary.
- **The synthetic "urgent_added" scenario** injects a delivery with an in-memory negative ID; it is never persisted.
- **No stochasticity.** Simulations are deterministic — running the same scenario twice produces the same numbers.

---

## AI / LLM

- **LLM is optional.** When `GEMINI_API_KEY` is missing, all answers are deterministic. The UI labels them `deterministic fallback`.
- **No function calling.** The LLM is used only to rephrase prose. It cannot call tools, run queries, or trigger actions.
- **No conversation memory across requests.** Each copilot query is stateless.
- **The customer draft LLM polish** is not asserted by tests against the real provider — only the deterministic path is verified in CI.

---

## Authentication / authorization

- **Single admin user only.** Created from `.env` credentials at seed time. No sign-up, no user management, no profile editing.
- **No roles / RBAC.** All authenticated actions are attributed to the same admin.
- **No CSRF token.** We rely on `HttpOnly` + `SameSite=Lax` cookies + POST-only mutations + same-origin CORS. Adequate for a demo; **not** what you'd ship publicly.
- **No password rotation flow.** To change the password: edit `ADMIN_PASSWORD` in `.env`, delete `backend/brainflow.db`, run `alembic upgrade head` and `python -m scripts.seed`.
- **Read endpoints are public.** Intentional (browsing the demo without login). Mutations require auth.
- **No account lockout or rate limiting on `/api/auth/login`.**

---

## External integrations

- **Open-Meteo and Nager.Date are optional.** If unreachable, deterministic demo values (weather) or an empty list (holidays) are returned. Both paths are handled but only the fallback is exercised in CI.
- **No caching across process restarts.** In-memory `dict` cache only; restarts clear it.
- **No proxy-aware HTTPS handling.** `COOKIE_SECURE=false` by default (localhost). Set `COOKIE_SECURE=true` behind HTTPS.

---

## Background scheduler

- **In-process APScheduler.** Runs in the same worker as the API. Not intended for **multi-instance** deployment — you would need a distributed scheduler (Redis + Celery or similar) for that.
- **No persistence of job store.** If the app restarts, the schedule restarts from the next interval.
- **Disableable via `SCHEDULER_ENABLED=false`.**
- **Not exercised by automated tests** to avoid flaky timing; verified manually during development (see `docs/TESTING.md`).

---

## Frontend

- **Single ~1 MB JS chunk.** Vite warns at >500 kB. Route-level code splitting (`React.lazy` per page) would reduce it; **not implemented** in this build.
- **No dark mode.** The design system is deliberately light/neutral; dark mode tokens exist but the UI does not expose a toggle.
- **No mobile bottom-nav.** The sidebar hides on small screens; only the desktop experience is polished. Responsive behavior is limited to hiding the sidebar.
- **Very small number of frontend tests.** 16 tests across 6 files, focused on critical components and flows. Full coverage of all 11 pages is **not** present.
- **No Playwright E2E tests** in the default `npm run test` — the workflow is exercised manually per `docs/DEMO_GUIDE.md`.

---

## Lint

- **3 informational warnings** (`react-hooks/incompatible-library` for React Hook Form's `watch()` — memoization is skipped, functionally irrelevant).
- **1 file-scoped disable** (`useAuth.tsx`) for `react-refresh/only-export-components` + `react-hooks/set-state-in-effect` — a documented, safe pattern for the async status fetch on mount.

`npm run lint` outputs **0 errors, 3 warnings**.

---

## Testing gaps

- **No performance / load tests.** Not applicable for a demo.
- **No a11y automated audit** (axe-core). Semantic HTML is used but not asserted.
- **No visual regression tests.**
- **No test for the real Gemini provider.** Only the fallback path is verified.
- **No test for live weather/holiday responses.** Only the fallback path is verified.

---

## Operational

- **SQLite is used by default.** Works fine for the demo (single-writer, tiny data). The `DATABASE_URL` can be pointed at PostgreSQL but that path is not exercised by CI.
- **No migrations rollback UI.** Standard Alembic commands only.
- **No backups.**
- **No metrics/observability stack.** `/api/health` returns structured status.

---

## What is intentionally *not* a limitation

For clarity, these are **by design** and would still apply to a production build:

- No automatic customer notifications — drafts only, requires human action
- Risk scores are labelled as rule-based, not ML
- Customer drafts are always marked `requires_human_review: true`
- Execution requires approval; revalidation prevents stale application
- Audit trail is append-only

---

## If this were extended

- Add a **stochastic or history-based** risk model once real data exists
- Add **per-vehicle sequencing** to the planner
- Add **authentication with multiple roles** (operator, manager, admin)
- Add **Playwright E2E** for the full demo workflow
- **Route-split** the frontend bundle
- **Distribute** the scheduler with Redis / Celery and a persistent job store
- Add **CSRF tokens** and rate limiting on auth endpoints
- Add **PostgreSQL** integration tests and a migration CI
