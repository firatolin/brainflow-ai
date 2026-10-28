#!/usr/bin/env bash
set -u
BASE=http://127.0.0.1:8000
echo "== 1) Generate plans =="
PLANS=$(curl -s -X POST $BASE/api/plans/generate)
echo "$PLANS" | python -c "import sys,json; [print(p['id'], p['kind'], 'feasible='+str(p['feasible'])) for p in json.load(sys.stdin)]"
PLAN_ID=$(echo "$PLANS" | python -c "
import sys, json
ps = json.load(sys.stdin)
cands = [p for p in ps if p['feasible'] and p['kind'] != 'baseline']
if not cands: cands = [p for p in ps if p['feasible']]
print(cands[0]['id'] if cands else '')
")
echo "Picked PLAN_ID=$PLAN_ID"
if [ -z "$PLAN_ID" ]; then echo "No feasible plan — aborting"; exit 1; fi
echo ""
echo "== 2) Submit plan $PLAN_ID =="
SUBMIT=$(curl -s -X POST $BASE/api/plans/$PLAN_ID/submit -H 'Content-Type: application/json' -d '{"actor":"operator"}')
echo "$SUBMIT" | python -m json.tool || { echo "SUBMIT failed"; exit 1; }
ACTION_ID=$(echo "$SUBMIT" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "ACTION_ID=$ACTION_ID"
echo ""
echo "== 3) Approve =="
curl -s -X POST $BASE/api/actions/$ACTION_ID/approve -H 'Content-Type: application/json' -d '{"reviewer":"supervisor","note":"approved"}' | python -m json.tool
echo ""
echo "== 4) Execute (1st) =="
curl -s -X POST $BASE/api/actions/$ACTION_ID/execute -H 'Content-Type: application/json' -d '{"reviewer":"supervisor"}' | python -m json.tool
echo ""
echo "== 5) Execute (2nd, idempotent) =="
curl -s -X POST $BASE/api/actions/$ACTION_ID/execute -H 'Content-Type: application/json' -d '{"reviewer":"supervisor"}' | python -m json.tool
echo ""
echo "== 6) Audit events =="
curl -s "$BASE/api/audit-events?entity_type=operational_action&entity_id=$ACTION_ID&page_size=50" | python -c "
import sys, json
b = json.load(sys.stdin)
print(f'total={b[\"total\"]}')
for e in b['items']: print(' ', e['event_type'], 'by', e['actor'])
"
