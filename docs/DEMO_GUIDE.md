
# Demo Guide — 15 minutes

## Preparation

Terminal 1 (backend):
```bash
cd backend
source .venv/bin/activate
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload --port 8000 --log-config uvicorn.log_config.json
```

Terminal 2 (frontend):
```bash
cd frontend
npm run dev
```

Open http://localhost:5173 · Login: admin / BrainFlow@2026

## Walkthrough

1. Overview — baseline: Active 40, At-risk 0 (no scan yet), Active vehicles 5, Open incidents 0
2. Run scan (topbar) — toast; Open incidents rises (~15); At-risk rises
3. Exceptions — grouped by severity. Acknowledge one, resolve another
4. Recovery — Generate plans → 3 cards: baseline (infeasible due to MBK-01), minimize_delays (feasible), balanced (feasible). Select minimize_delays → Submit for approval
5. Approvals — Approve → Execute. Toast shows Applied N changes. Execute again → no-op (idempotent)
6. Deliveries — reassignments visible; click a delivery → History shows changes
7. Audit — search "Admin" → action.submitted, action.approved, delivery.reassigned × N, action.executed (exactly once)
8. Simulations — Vehicle unavailable + VAN-01 → Run. See baseline / no-recovery / recovered deltas
9. Copilot — ask "Which deliveries are most likely to be late?" → answer labelled deterministic fallback (or llm)
10. Analytics — measured stats, risk distribution, 14-day trend, plan comparison
11. Settings — app info, admin account, system status, external context sources

## Reset DB

```bash
cd backend
rm -f brainflow.db
alembic upgrade head
python -m scripts.seed
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| Login fails | Confirm ADMIN_PASSWORD=BrainFlow@2026 in .env |
| Weather source demo | Network offline — expected |
| Not authenticated | Session expired — sign in again |
| Empty pages | Backend not running |
| CORS error | Set CORS_ORIGINS in .env |
| Scheduler silent | SCHEDULER_ENABLED=true + --log-config uvicorn.log_config.json |
