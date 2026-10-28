# Technical Decisions

A working log of the non-trivial engineering choices in BrainFlow AI, with the reasoning behind each.

---

## 1. FastAPI + SQLAlchemy + Alembic

**Chosen:** FastAPI for the API, SQLAlchemy 2.x ORM, Alembic for migrations.

**Why:**

- FastAPI gives us async request handling, automatic OpenAPI (so `/docs` is useful for the assignment reviewer), and Pydantic validation that maps directly onto the request/response contracts
- SQLAlchemy 2.x `Mapped[...]` annotations give typed columns + first-class Alembic support
- Alembic was essential when we evolved the schema 6 times during development — no schema drift
- SQLite by default (zero setup) with a one-variable path to PostgreSQL

**Trade-off:** SQLAlchemy 2.1 required Python 3.14 wheels; we hit a pre-existing `TypeError` on SQLAlchemy 2.0.36 and upgraded. This is documented in `KNOWN_LIMITATIONS.md` for anyone pinning versions.

---

## 2. Synchronous SQLAlchemy, not async

**Chosen:** synchronous engine + `Session`.

**Why:**

- FastAPI's `Depends` + `run_in_threadpool` handles sync routes cleanly
- Avoids `greenlet` ABI issues on newer Python
- Our workloads are tiny — sync is fast enough and vastly simpler
- Background scheduler also uses sync sessions; APScheduler runs jobs in its own thread

**Trade-off:** not suitable for high-concurrency production without moving to async, but that's out of scope.

---

## 3. Rule-based risk engine (not ML)

**Chosen:** deterministic weighted-sum scoring with a documented formula.

**Why:**

- No historical labeled dataset of late deliveries exists — a "trained model" would be an invented number
- Deterministic scores are **testable, reproducible, and explainable** — critical for operational trust
- The formula directly encodes operational intuition (deadline pressure, delay, weather, priority, data quality)
- Confidence is reported separately from score, so an operator knows when data is weak

**What this is *not*:** a statistically-trained predictor. It is a rule-based estimate, and both the UI and API labels it as such.

---

## 4. Incident deduplication via stable identity

**Chosen:** `(kind, entity_type, entity_id, discriminator)` tuple as the identity key.

**Why:**

- The scheduler runs every 5 min; without dedup we'd create thousands of duplicate rows and drive the operator mad
- A scan should **reinforce** existing incidents, not spawn new ones
- Auto-resolve when the condition clears; auto-reopen when it returns
- Tested in `test_dedup_same_condition_across_scans` and `test_auto_resolve_when_condition_gone`

**Alternative rejected:** storing incidents only for "new" events without dedup — loses track of ongoing state.

---

## 5. Greedy planner, not OR-Tools

**Chosen:** greedy local improvement with a feasibility repair pass.

**Why:**

- The problem is a **constrained assignment/sequencing variant**, not a full VRP — a solver would be overkill
- The greedy algorithm is **deterministic, explainable, and testable**
- The repair pass is essential: seed data intentionally contains a capacity violation to demonstrate it
- We explicitly do **not** claim optimality — the docs say "rule-based heuristic"

**What we tested:**

- Baseline plan never changes anything
- Planner respects capacity
- Planner repairs pre-existing infeasibility
- Same inputs → identical output (determinism)
- Three plans returned (`baseline`, `minimize_delays`, `balanced`)

**Trade-off:** a future version could add LP/CP-SAT for larger fleets.

---

## 6. What-if simulation on isolated snapshots

**Chosen:** deep-copy dataclasses; never touch DB rows.

**Why:**

- The user expects to run many what-ifs without consequence
- A "simulation" that mutates rows would be dangerous and untrustworthy
- Snapshot approach makes it trivial to compute baseline / no-recovery / recovered triple for the same scenario
- Test `test_simulation_does_not_touch_db` asserts the invariant

---

## 7. Human approval + stale-plan revalidation

**Chosen:** `DRAFT → PENDING_APPROVAL → APPROVED → EXECUTED` lifecycle with revalidation before execution.

**Why:**

- The assignment's central safety requirement is: **no consequential change without approval**
- Between plan generation and execution, the world can change (delivery delivered, vehicle out of service). Execution **must not** blindly apply stale diffs
- We snapshot the "before" state at submission; execution compares current assignments to that snapshot. Any drift → `409 stale-plan` → operator must refresh
- **Idempotent** execution (`status == EXECUTED` short-circuits) prevents accidental double-apply from UI double-clicks or network retries

**What we tested** (`test_approval_flow.py`, `test_audit.py`):

- Submit → approve → execute happy path
- Execute **requires** approval (409 otherwise)
- Execute **is idempotent** (2nd call returns the same result, `action.executed` appears once in audit)
- Rejection prevents execution
- Drift in DB state causes execution to return 409 with reasons
- Audit trail records submission, approval, execution

---

## 8. Append-only audit trail

**Chosen:** `AuditEvent` rows written only via `audit_service.record()`; no update or delete endpoints.

**Why:**

- The audit trail is the *only* trustworthy record of consequential changes
- Consequential changes are: plan submitted, approved, rejected, executed, delivery reassigned, incident events, etc.
- Recorded as event_type + entity_type + entity_id + context_json + actor + timestamp

**Trade-off:** no cryptographic tamper-evidence (would need a hash chain); acceptable for a demo.

---

## 9. Deterministic fallback for LLM

**Chosen:** LLM provider abstraction with a `FallbackProvider` that returns `None` for any generation call. All LLM call sites must handle `None` by falling back to deterministic logic.

**Why:**

- The assignment explicitly forbids "fabricating API calls"
- A reviewer without a `GEMINI_API_KEY` must still see a working product
- The copilot and customer-draft flows are designed so **facts come from the DB, not the LLM** — the LLM only rephrases. If it fails, we drop the rephrase and show the deterministic answer with a clear label

**What we tested** (`test_copilot.py`, `test_customer_drafts.py`):

- Copilot answers deterministically when no key is set
- Customer drafts use `source: "template"` when no key is set
- `/api/health` reports `ai.provider = "fallback"`

---

## 10. Bounded copilot — no arbitrary tool execution

**Chosen:** 4 question routes → 4 deterministic answer generators. The LLM sees only the curated facts from those generators.

**Why:**

- The assignment forbids unrestricted tool execution or arbitrary DB queries from the LLM
- Every answer is built by our code, then optionally rephrased — the LLM cannot invent a delivery ID
- Prompt says "Do NOT invent delivery IDs, vehicle codes, or facts"
- Facts are JSON-encoded in the prompt, so the model has them verbatim

**Alternative rejected:** free-form LLM tool use — hard to bound, hard to test, easy to hallucinate.

---

## 11. Auth: single admin, bcrypt + server-side sessions

**Chosen:** one seeded admin from `.env`; bcrypt hashed password; **server-side** sessions with hashed token at rest in a `sessions` table; HttpOnly SameSite=Lax cookie.

**Why:**

- The product needs *an* operator identity to attribute approvals to (the assignment explicitly calls for human approval)
- The assignment's §10 says: "If time does not permit a complete auth system, clearly document the local-demo trust boundary" — but we had time, so we built a minimal real login
- Server-side sessions (vs JWT) are simpler to invalidate and appropriate for a single-user demo
- Reads stay public; only **mutations** are gated. This matches the demo's intent — the reviewer can browse data without logging in, but **cannot change state** without being `Admin`

**Not implemented:**

- CSRF token (relies on `SameSite=Lax` + POST-only mutations + same-origin CORS)
- Multi-user roles / RBAC
- Password rotation UI

Documented honestly in `KNOWN_LIMITATIONS.md`.

---

## 12. APScheduler in-process

**Chosen:** `BackgroundScheduler` started in FastAPI's `lifespan`; every `SCAN_INTERVAL_MINUTES`; `max_instances=1`; disableable.

**Why:**

- No external broker to install (Redis / RabbitMQ) — right-sized for the demo
- `max_instances=1` prevents overlap
- Disabled in tests (`SCHEDULER_ENABLED` env / lifespan not triggered via `TestClient`)
- `coalesce=True` prevents backlog if the app was paused

**Trade-off:** not designed for multi-worker / multi-instance deployment — documented.

---

## 13. External APIs with cache + graceful failure

**Chosen:** `httpx` client with `EXTERNAL_TIMEOUT_SECONDS`; in-memory cache; deterministic fallback.

**Why:**

- Open-Meteo and Nager.Date are nice-to-have context, not core
- A demo reviewer might be offline — the app must not break
- Cache TTLs: 10 min (weather), 6 h (holidays)

**What we tested:** weather and holidays return either real data (`source: "open-meteo"` / `"nager"`) or demo/empty fallback — both work.

---

## 14. Frontend: Vite + React 19 + TS strict

**Chosen:** Vite 8, React 19, TypeScript strict, Tailwind 3, shadcn-style primitives (Radix + CVA), TanStack Query, React Router.

**Why:**

- Strict TS catches integration issues at build time — we found 8 pre-release bugs this way
- TanStack Query handles caching, polling, and invalidation cleanly
- Tailwind 3 + a small set of Radix primitives gave us a **restrained B2B aesthetic** — no gradients, no glassmorphism, semantic badges only where needed
- We deliberately didn't run `npx shadcn add` — hand-wrote the primitives we actually use so nothing extra ships

**Trade-off:** the frontend bundle is one ~1 MB chunk (Recharts is ~400 kB of that). Route-level code splitting is a documented follow-up.

---

## 15. Testing strategy

**Backend** — pytest with in-memory SQLite per test (`StaticPool` so all sessions see the same connection). No live external APIs. **73 tests** cover the risk engine, planner, simulator, approvals, auth, everything.

**Frontend** — Vitest + React Testing Library with mocked `fetch`. **16 tests** across 6 files. Focused on: KPI rendering, badge mapping, login flow (validation + submit), deliveries list, overview KPIs, utility merge.

**What we didn't do:**

- Snapshot tests (brittle and low-value for this UI)
- Playwright E2E (optional; `docs/DEMO_GUIDE.md` provides the equivalent manual flow)

---

## 16. Known ESLint trade-offs

ESLint 10's `react-hooks/set-state-in-effect` rule flagged our `useAuth` refresh pattern. The pattern is correct (async fetch on mount, awaited before `setState`) — the runtime in React 19 does not warn. We added a **file-level disable** with a comment and documented the reasoning.

Three `react-hooks/incompatible-library` warnings remain — they are for `watch()` from React Hook Form. React Compiler will skip memoization for those components. Functionally irrelevant.

The lint output is **0 errors, 3 informational warnings**.
