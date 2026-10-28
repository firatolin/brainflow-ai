
# Known Limitations

## Scope

- Demonstration data only — all deliveries, vehicles, outcomes synthetic
- No real external logistics integrations
- No payments/invoicing
- No historical dataset — rule-based risk, not trained ML

## Risk engine

- Rule-based (documented formula), not statistically trained
- Confidence heuristic, not statistical interval
- Fixed 25 km/h travel assumption

## Optimizer

- Greedy heuristic, not optimal
- No vehicle sequencing (only assignments)
- No multi-depot / time-window modeling
- Distances/costs from seed data

## Simulations

- Estimate only
- urgent_added uses in-memory negative ID — never persisted
- Deterministic (no stochasticity)

## AI

- LLM optional; deterministic path when no key
- No function calling — rephrases only
- No conversation memory
- Real Gemini provider not asserted in tests (fallback path only)

## Auth

- Single admin — no sign-up or user management
- No roles / RBAC
- No CSRF token (SameSite=Lax + POST-only + CORS)
- No password rotation flow
- Reads public for demo friendliness
- No login rate limiting

## External

- Open-Meteo / Nager.Date optional; fallbacks only exercised in CI
- In-memory cache only (cleared on restart)
- COOKIE_SECURE=false default

## Scheduler

- In-process APScheduler — not multi-instance safe
- No persistent job store (schedule restarts on app restart)
- Disableable via SCHEDULER_ENABLED=false

## Frontend

- Single ~1 MB bundle — route splitting is a follow-up
- No dark mode toggle (tokens exist)
- No mobile bottom-nav (sidebar hides)
- 16 frontend tests focus on critical flows, not full coverage
- Playwright E2E not included by default

## Lint

- 3 informational warnings (react-hooks/incompatible-library for React Hook Form's watch())
- 1 file-scoped disable in useAuth.tsx with rationale in code
- npm run lint → 0 errors, 3 warnings

## Testing gaps

- No performance / load tests
- No automated a11y audit
- No visual regression
- No test for real Gemini or live Open-Meteo/Nager.Date

## Operational

- SQLite default (fine for demo)
- No backups
- No metrics / observability beyond /api/health

## Intentionally not limitations

- No auto-send customer messages — drafts only (by design)
- Risk scores labeled rule-based (by design)
- Drafts marked requires_human_review: true (by design)
- Execution requires approval (by design)
- Audit append-only (by design)
