# BrainFlow AI — Architecture

## System diagram

    flowchart LR
        subgraph FE[Frontend · React 19 + Vite + TS]
          UI[Pages
          Overview · Deliveries · Fleet · Exceptions · Recovery ·
          Simulations · Copilot · Analytics · Approvals · Audit · Settings]
          Query[TanStack Query
          cache + polling]
          API[Typed API client
          /api/*]
          Auth[AuthProvider
          session cookie]
        end

        subgraph BE[Backend · FastAPI]
          Router[API routers]
          Authz[require_user
          dependency]
          Svc[Services:
          risk · incidents · planner · simulator ·
          approvals · audit · analytics · dashboard · copilot]
          ORM[SQLAlchemy models]
          Sched[APScheduler
          5m scan]
          LLM[LLM provider
          Gemini / fallback]
          Ext[Open-Meteo · Nager.Date
          cached with demo fallback]
        end

        DB[(SQLite / PostgreSQL)]

        UI --> Query --> API --> Router
        Router --> Authz --> Svc --> ORM --> DB
        Sched --> Svc
        Svc --> LLM
        Svc --> Ext

## Layers

### 1. API layer (`backend/app/api/`)

- Thin routers with Pydantic validation
- Every mutating route guarded by `Depends(require_user)` (cookie session)
- Read routes are public (deliberate, for demo friendliness)
- Pagination, filtering, sorting consistent across listing endpoints
- Errors return structured `{"detail": ...}` with appropriate status codes

### 2. Service layer (`backend/app/services/`)

Pure, testable business logic. No httpx calls, no LLM calls from the API layer — it all goes through services.

- `risk_engine` — pure function, deterministic, 5-factor weighted score
- `incident_service` — detects conditions, dedups via `(kind, entity_type, entity_id, discriminator)`
- `scan_service` — orchestrates assessment + incident detection + scan_run persistence
- `optimizer.planner` — greedy local improvement on `(late, priority_delay, total_delay, cost, changes)` objective
- `optimizer.objective` — shared evaluator + feasibility checker
- `simulator` — snapshot-only — never mutates production rows
- `approval_service` — approval lifecycle + stale-plan revalidation + idempotent execution
- `audit_service` — append-only writes only
- `dashboard_service` / `analytics_service` — read aggregation
- `copilot_service` — tool-bounded answers; LLM used only to rephrase
- `scheduler` — APScheduler wrapper
- `seed` — deterministic demo scenario

### 3. Model layer (`backend/app/models/`)

14 tables, all with proper FKs, indexes, and timezone-aware timestamps:

- `deliveries`, `delivery_history`
- `vehicles`
- `risk_assessments`, `incidents`, `scan_runs`
- `recovery_plans`, `recovery_plan_items`, `simulations`
- `operational_actions`, `approvals`, `audit_events`
- `users`, `sessions`

### 4. Integration layer (`backend/app/integrations/`)

- `llm_client` — protocol-based provider abstraction: `GeminiProvider` or `FallbackProvider`. Never trusts the LLM for facts.
- `weather_client` — Open-Meteo with in-memory cache (10 min TTL), 6s timeout, deterministic demo fallback
- `holiday_client` — Nager.Date with 6h cache, graceful `[]` fallback

## Key algorithms

### Risk engine — `services/risk_engine.py`

Score (0..100) is a documented, deterministic weighted sum of five normalized factors. Not a trained model.

    score = 100 × (
        0.35 × deadline_pressure
      + 0.20 × current_delay
      + 0.15 × weather_exposure
      + 0.15 × priority_weight
      + 0.15 × (1 − data_confidence)
    )

where:
  deadline_pressure = f(minutes_left / eta_minutes)  ∈ [0, 1]
  current_delay     = min(1, delay_minutes / 120)    ∈ [0, 1]
  weather_exposure  = input (0..1)
  priority_weight   ∈ {0.10 low, 0.30 normal, 0.65 high, 1.00 urgent}
  data_confidence   ∈ [0.2, 1.0]  — penalty for missing vehicle/dispatch/ETA or stale update

eta_minutes = (max(distance_km, 0.5) / 25 km/h) × 60

category:
  0-24    low
  25-49   medium
  50-74   high
  75-100  critical

Assessed: reproducible — given identical inputs, identical score.

### Incident detection — `services/incident_service.py`

Detected kinds:

| Kind | Trigger |
|---|---|
| `late_likely` | risk_score ≥ 50 |
| `vehicle_unavailable` | assigned delivery with unavailable vehicle |
| `capacity_exceeded` | vehicle active deliveries > capacity |
| `severe_weather` | weather_exposure ≥ 0.5 |
| `unassigned_high_priority` | priority ∈ {high, urgent} and vehicle_id = null |
| `conflicting_assignment` | reserved for future — reserved identifier |
| `missing_info` | missing dispatch / deadline / distance |
| `stale_estimate` | not updated in >6h |

Stable identity = `(kind, entity_type, entity_id, discriminator)`. Repeated scans do not create duplicates. Resolved incidents auto-reopen if the condition returns. Open incidents auto-resolve if the condition clears.

### Planner — `services/optimizer/planner.py`

Objective (documented, tested):

    cost(plan) =
        8.0  × late_deliveries
      + 1.0  × Σ (priority_weight × delay_minutes)
      + 0.2  × Σ delay_minutes
      + 0.5  × extra_cost
      + 2.0  × num_changes

Constraints:

- Only available vehicles can receive deliveries
- Vehicle capacity is enforced (active deliveries ≤ capacity)
- Terminal deliveries are excluded

Algorithm:

1. Baseline = current assignments
2. Feasibility repair pass — for each over-capacity vehicle, move lowest-priority deliveries to available vehicles with room; for each unavailable-assigned delivery, reassign to an available vehicle
3. Greedy local improvement over candidate set (risk_score ≥ 50, or urgent/high & unassigned, or assigned to an unavailable vehicle)
4. Return three plans: `baseline`, `minimize_delays`, `balanced` (higher cost weight)

Not claimed to be optimal. Deterministic. Documented as a greedy heuristic.

### Simulator — `services/simulator.py`

- Snapshots current state into plain dataclasses
- Applies scenario to the snapshot only
- Computes:
  - baseline metrics (no changes)
  - "no-recovery" metrics (scenario applied, assignments unchanged)
  - "recovered" metrics (scenario applied, plan generated and applied in-memory)
- Returns explicit deltas → comparison UI shows before / hypothetical / recovered
- Never mutates DB rows. Test `test_simulation_does_not_touch_db` verifies this.

### Approval + execution — `services/approval_service.py`

    DRAFT → PENDING_APPROVAL → APPROVED → EXECUTED
                          ↘ REJECTED

- Submit: snapshot current state into `before_state_json`; record `proposed_state_json`
- Approve: reviewer decided; plan status → approved; audit
- Execute:
  - Idempotency — if status == EXECUTED, return existing result immediately
  - Revalidation — compare current DB assignments to before_state_json; if any drift → 409 stale
  - Feasibility re-check — vehicles still exist, available, within capacity
  - Apply — update delivery.vehicle_id per item, write audit per row
  - Persist execution_result and mark executed
- Any revalidation failure blocks execution and writes an audit event.

### Copilot — `services/copilot_service.py`

Deterministic routing on the question → one of: `deliveries_at_risk`, `priority_deliveries`, `biggest_risk`, `situation_summary`

- Base answer built from DB queries
- If Gemini is available: sends only the curated facts object + base answer to the model for rephrasing. Nothing the model produces is trusted for facts.
- If Gemini is unavailable: returns deterministic answer + explicit note

Customer drafts (`services/message_service.py`) are similar: template fallback + optional LLM polish.

## Data flow (end-to-end demo)

    Seed ──▶ DB
      │
      ▼
    Background scan / manual scan
      │  ── risk_engine.assess(delivery, vehicle)
      │  ── risk_assessments insert
      │  ── incident_service.detect_all(db)
      │  ── incident_service.apply(db, detections)  [dedup]
      │  ── scan_runs insert
      ▼
    Exceptions page — user acknowledges / resolves
      │
      ▼
    Recovery page — planner.generate_plans()
      │  ── baseline + minimize_delays + balanced
      ▼
    User picks a plan and clicks "Submit for approval"
      │  ── operational_actions insert (PENDING_APPROVAL)
      │  ── approvals insert (PENDING)
      ▼
    Approvals page — user approves
      │  ── status → APPROVED
      ▼
    User executes
      │  ── revalidate ── feasible? ── else 409
      │  ── apply delivery.vehicle_id changes
      │  ── audit_events write per delivery + summary
      │  ── status → EXECUTED
      ▼
    Audit page — every step searchable
    Analytics page — aggregates reflect persisted state

## Frontend

- Router — `/login`, then protected shell with 11 pages
- Auth — `AuthProvider` fetches `/api/auth/status` on mount; `ProtectedRoute` redirects to `/login` when anonymous
- Query client — `staleTime: 15s`, `refetchOnWindowFocus: false`; per-page `refetchInterval` where appropriate
- Toasts — Sonner; success and error variants
- Design system — neutral white surfaces, single blue accent, semantic badges, subtle borders. No gradients, glassmorphism, or decorative animation.
- Charts — Recharts with `strokeWidth={1.5}`, `fillOpacity={0.08}`, muted grid `#f1f5f9`

## Reliability and safety guarantees

- Mutations require auth — `Depends(require_user)` on every POST/PATCH
- Stale-plan rejection — execution revalidates against current DB state
- Idempotent execution — safe to retry
- Append-only audit — writes only via service
- Deterministic fallbacks — the app works without any external API or LLM
- Scan deduplication — no duplicate incidents across repeated runs
- No auto-send — customer messages are drafts; approval required

Full limitations: `docs/KNOWN_LIMITATIONS.md`.
