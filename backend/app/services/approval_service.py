"""Human-approval workflow + safe execution of operational changes."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.models.approval import Approval, ApprovalDecision
from app.models.delivery import Delivery, DeliveryStatus
from app.models.operational_action import ActionStatus, OperationalAction
from app.models.recovery_plan import PlanStatus, RecoveryPlan
from app.models.vehicle import Vehicle, VehicleStatus
from app.services import audit_service


ACTIVE_STATUSES = (
    DeliveryStatus.PENDING,
    DeliveryStatus.ASSIGNED,
    DeliveryStatus.IN_TRANSIT,
    DeliveryStatus.DELAYED,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------- Snapshot helpers ----------

def _snapshot_active_assignments(db: Session) -> dict[int, int | None]:
    out: dict[int, int | None] = {}
    for d in db.query(Delivery).filter(Delivery.status.in_(ACTIVE_STATUSES)).all():
        out[d.id] = d.vehicle_id
    return out


def _plan_to_assignments_map(plan: RecoveryPlan) -> dict[int, int | None]:
    return {item.delivery_id: item.to_vehicle_id for item in plan.items}


# ---------- Submit ----------

def submit_plan(db: Session, plan_id: int, *, actor: str = "system") -> OperationalAction:
    plan = db.get(RecoveryPlan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    if plan.status != PlanStatus.DRAFT:
        raise HTTPException(409, f"Plan status is {plan.status.value}; only 'draft' can be submitted")
    if not plan.feasible:
        raise HTTPException(409, "Cannot submit an infeasible plan")

    before = _snapshot_active_assignments(db)
    proposed = _plan_to_assignments_map(plan)

    action = OperationalAction(
        action_type="recovery_plan",
        plan_id=plan.id,
        status=ActionStatus.PENDING_APPROVAL,
        before_state_json=json.dumps(before),
        proposed_state_json=json.dumps(proposed),
        expected_impact=plan.explanation,
        reason=f"Recovery plan {plan.kind.value} with {plan.changes_count} change(s)",
        requested_at=_now(),
    )
    db.add(action)
    db.flush()

    db.add(Approval(action_id=action.id, decision=ApprovalDecision.PENDING))

    plan.status = PlanStatus.SUBMITTED

    audit_service.record(
        db, "action.submitted",
        entity_type="operational_action", entity_id=action.id,
        actor=actor,
        context={"plan_id": plan.id, "kind": plan.kind.value, "changes": plan.changes_count},
    )

    db.commit()
    db.refresh(action)
    return action


# ---------- Approve / Reject ----------

def _get_action_pending(db: Session, action_id: int) -> OperationalAction:
    action = db.get(OperationalAction, action_id)
    if not action:
        raise HTTPException(404, "Action not found")
    if action.status != ActionStatus.PENDING_APPROVAL:
        raise HTTPException(
            409, f"Action status is {action.status.value}; only 'pending_approval' can be decided"
        )
    return action


def _update_approval(db: Session, action_id: int, decision: ApprovalDecision,
                     reviewer: str, note: str | None) -> Approval:
    ap = (
        db.query(Approval)
        .filter(Approval.action_id == action_id)
        .order_by(Approval.id.desc())
        .first()
    )
    if not ap:
        ap = Approval(action_id=action_id)
        db.add(ap)
    ap.decision = decision
    ap.reviewer = reviewer
    ap.note = note
    ap.decided_at = _now()
    return ap


def approve_action(db: Session, action_id: int, *, reviewer: str, note: str | None = None) -> OperationalAction:
    action = _get_action_pending(db, action_id)
    action.status = ActionStatus.APPROVED
    action.reviewer = reviewer
    action.decided_at = _now()

    _update_approval(db, action.id, ApprovalDecision.APPROVED, reviewer, note)

    if action.plan_id:
        plan = db.get(RecoveryPlan, action.plan_id)
        if plan:
            plan.status = PlanStatus.APPROVED

    audit_service.record(
        db, "action.approved",
        entity_type="operational_action", entity_id=action.id,
        actor=reviewer,
        context={"note": note, "plan_id": action.plan_id},
    )
    db.commit()
    db.refresh(action)
    return action


def reject_action(db: Session, action_id: int, *, reviewer: str, note: str | None = None) -> OperationalAction:
    action = _get_action_pending(db, action_id)
    action.status = ActionStatus.REJECTED
    action.reviewer = reviewer
    action.decided_at = _now()

    _update_approval(db, action.id, ApprovalDecision.REJECTED, reviewer, note)

    if action.plan_id:
        plan = db.get(RecoveryPlan, action.plan_id)
        if plan:
            plan.status = PlanStatus.REJECTED

    audit_service.record(
        db, "action.rejected",
        entity_type="operational_action", entity_id=action.id,
        actor=reviewer,
        context={"note": note, "plan_id": action.plan_id},
    )
    db.commit()
    db.refresh(action)
    return action


# ---------- Execute (revalidate + apply + audit) ----------

def _revalidate(db: Session, action: OperationalAction) -> list[str]:
    """Return list of drift reasons; empty = safe to execute."""
    reasons: list[str] = []
    before = json.loads(action.before_state_json or "{}")
    proposed = json.loads(action.proposed_state_json or "{}")

    # 1) any delivery in before snapshot must still have the same vehicle_id
    current = _snapshot_active_assignments(db)
    for did_str, expected_vid in before.items():
        did = int(did_str)
        current_vid = current.get(did)
        if current_vid != expected_vid:
            reasons.append(
                f"delivery {did} assignment drifted (was {expected_vid}, now {current_vid})"
            )

    # 2) proposed vehicles must still exist, be available, and not be over capacity after apply
    vehicles = {v.id: v for v in db.query(Vehicle).all()}
    proposed_load: dict[int, int] = {}
    for did_str, vid in proposed.items():
        did = int(did_str)
        if vid is None:
            continue
        v = vehicles.get(vid)
        if not v:
            reasons.append(f"vehicle {vid} no longer exists")
            continue
        if not v.available or v.status != VehicleStatus.AVAILABLE:
            reasons.append(f"vehicle {v.code} is no longer available")
        # skip terminal deliveries
        d = db.get(Delivery, did)
        if d and d.status in (DeliveryStatus.DELIVERED, DeliveryStatus.CANCELLED, DeliveryStatus.FAILED):
            continue
        proposed_load[vid] = proposed_load.get(vid, 0) + 1

    for vid, n in proposed_load.items():
        v = vehicles.get(vid)
        if v and n > v.capacity:
            reasons.append(f"vehicle {v.code} would be over capacity ({n}/{v.capacity})")

    return reasons


def execute_action(db: Session, action_id: int, *, reviewer: str = "system") -> OperationalAction:
    action = db.get(OperationalAction, action_id)
    if not action:
        raise HTTPException(404, "Action not found")

    # Idempotency
    if action.status == ActionStatus.EXECUTED:
        return action

    if action.status != ActionStatus.APPROVED:
        raise HTTPException(
            409, f"Action status is {action.status.value}; only 'approved' can be executed"
        )

    # Revalidate
    drift = _revalidate(db, action)
    if drift:
        audit_service.record(
            db, "action.execution_blocked",
            entity_type="operational_action", entity_id=action.id,
            actor=reviewer, context={"reasons": drift},
        )
        db.commit()
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail={"message": "Plan is stale; refresh and resubmit", "reasons": drift},
        )

    # Apply
    proposed = json.loads(action.proposed_state_json or "{}")
    applied = 0
    per_item: list[dict[str, Any]] = []
    for did_str, new_vid in proposed.items():
        did = int(did_str)
        d = db.get(Delivery, did)
        if not d:
            continue
        if d.status in (DeliveryStatus.DELIVERED, DeliveryStatus.CANCELLED, DeliveryStatus.FAILED):
            continue
        old_vid = d.vehicle_id
        if old_vid == new_vid:
            continue
        d.vehicle_id = new_vid
        # if reassigned from None → set status to assigned
        if new_vid is not None and d.status == DeliveryStatus.PENDING:
            d.status = DeliveryStatus.ASSIGNED
        elif new_vid is None and d.status == DeliveryStatus.ASSIGNED:
            d.status = DeliveryStatus.PENDING

        per_item.append({"delivery_id": did, "from": old_vid, "to": new_vid})
        applied += 1

        audit_service.record(
            db, "delivery.reassigned",
            entity_type="delivery", entity_id=did,
            actor=reviewer,
            context={"from_vehicle_id": old_vid, "to_vehicle_id": new_vid, "action_id": action.id},
        )

    result = {
        "applied_changes": applied,
        "items": per_item,
        "executed_at": _now().isoformat(),
    }
    action.status = ActionStatus.EXECUTED
    action.executed_at = _now()
    action.execution_result = json.dumps(result)

    if action.plan_id:
        plan = db.get(RecoveryPlan, action.plan_id)
        if plan:
            plan.status = PlanStatus.EXECUTED

    audit_service.record(
        db, "action.executed",
        entity_type="operational_action", entity_id=action.id,
        actor=reviewer, context=result,
    )
    db.commit()
    db.refresh(action)
    return action
