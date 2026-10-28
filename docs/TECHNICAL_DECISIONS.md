
# Technical Decisions

## 1. FastAPI + SQLAlchemy + Alembic
OpenAPI for reviewer, Pydantic contracts, typed columns, 7 Alembic revisions. SQLite default, Postgres path via DATABASE_URL.

## 2. Synchronous SQLAlchemy
Simpler on Python 3.14 (no greenlet ABI issues). Fine for this workload. Testable.

## 3. Rule-based risk engine (not ML)
No labeled dataset — a "trained" model would be invented. Deterministic weighted sum of 5 factors. Confidence reported separately. Explicitly labeled "rule-based" in UI and API.

## 4. Incident dedup via stable identity
(kind, entity_type, entity_id, discriminator) prevents scan spam. Auto-resolve/reopen. Tested.

## 5. Greedy planner, not OR-Tools
Not a full VRP. Deterministic local improvement with a feasibility repair pass fixes pre-existing capacity violations. Not claimed optimal.

## 6. Simulator on isolated snapshots
Deep-copied dataclasses. Never touches DB. Enables baseline / no-recovery / recovered triple for the same scenario. Test asserts invariant.

## 7. Human approval + stale-plan revalidation
Snapshot "before" at submission. Revalidation catches drift → 409 with reasons. Idempotent execution (status == EXECUTED short-circuits).

## 8. Append-only audit
AuditEvent written only via audit_service.record(). No update/delete endpoints.

## 9. Deterministic LLM fallback
FallbackProvider returns None. Call sites handle by returning deterministic logic. Facts from DB; LLM only rephrases.

## 10. Bounded copilot
4 question routes → 4 deterministic answer generators. Prompt includes curated facts verbatim. Model cannot invent IDs.

## 11. Auth: single admin, bcrypt + sessions
Admin from .env. Bcrypt hash via passlib. Server-side sessions with SHA-256 hashed token. HttpOnly SameSite=Lax cookie. Reads public, mutations gated.

Not implemented: CSRF tokens, RBAC, password rotation UI. Documented in KNOWN_LIMITATIONS.md.

## 12. APScheduler in-process
BackgroundScheduler in FastAPI lifespan. max_instances=1, coalesce=True. Disabled in tests. Not for multi-worker deployment.

## 13. External APIs with cache + fallback
httpx with timeout; in-memory cache (10 min weather, 6 h holidays); deterministic fallback. App works fully offline.

## 14. Frontend Vite + React 19 + strict TS
Strict TS catches integration bugs. TanStack Query for cache. Hand-written shadcn-style primitives. Bundle ~1 MB single chunk (Recharts heavy) — route split is documented follow-up.

## 15. Testing
Backend: pytest + in-memory SQLite per test, StaticPool. 73 tests. No live external APIs. Frontend: Vitest + RTL, mocked fetch, 16 tests. No Playwright E2E (manual demo guide).

## 16. ESLint trade-offs
ESLint 10's react-hooks/set-state-in-effect flagged useAuth refresh pattern — file-scope disable with rationale. 3 react-hooks/incompatible-library warnings for React Hook Form's watch() — informational. npm run lint → 0 errors, 3 warnings.
