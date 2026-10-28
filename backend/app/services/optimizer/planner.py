"""Greedy local-improvement planner.

Steps:
  1. Build baseline from current assignments.
  2. **Repair infeasibility** (this is what makes simulations meaningful):
       - For any delivery assigned to an unavailable vehicle, try moving to
         an available vehicle with spare capacity.
       - For any over-capacity vehicle, move lowest-priority deliveries to
         available vehicles with spare capacity.
     Deterministic tie-break: cheapest cost_per_km, then lowest vehicle id.
  3. **Optimize at-risk candidates** (risk >= 50 OR urgent/high & unassigned OR
     now-unassigned-after-repair) via greedy local search.
  4. Return [baseline, minimize_delays, balanced].

Not claimed optimal. Deterministic: identical inputs → identical output.
"""
from __future__ import annotations

from app.services.optimizer.objective import (
    BALANCED_WEIGHTS,
    DEFAULT_WEIGHTS,
    check_feasibility,
    evaluate,
)
from app.services.optimizer.plan_types import (
    PRIORITY_WEIGHT,
    Assignment,
    DeliverySnapshot,
    PlanResult,
    VehicleSnapshot,
)


def _objective_score(metrics, weights) -> float:
    return (
        weights["late_count"] * metrics.late_count
        + weights["priority_delay"] * metrics.priority_weighted_delay
        + weights["total_delay"] * metrics.total_delay_minutes
        + weights["cost"] * metrics.extra_cost
        + weights["changes"] * metrics.changes
    )


def _baseline_assignments(deliveries: dict[int, DeliverySnapshot]) -> list[Assignment]:
    return [
        Assignment(delivery_id=d.id, vehicle_id=d.vehicle_id)
        for d in deliveries.values()
        if d.status not in ("delivered", "cancelled", "failed")
    ]


def _loads(assignments: list[Assignment], deliveries: dict[int, DeliverySnapshot]) -> dict[int, int]:
    load: dict[int, int] = {}
    for a in assignments:
        if a.vehicle_id is None:
            continue
        d = deliveries.get(a.delivery_id)
        if d is None or d.status in ("delivered", "cancelled", "failed"):
            continue
        load[a.vehicle_id] = load.get(a.vehicle_id, 0) + 1
    return load


def _spare_capacity(v: VehicleSnapshot, load: dict[int, int]) -> int:
    return v.capacity - load.get(v.id, 0)


def _eligible_vehicles(vehicles: dict[int, VehicleSnapshot]) -> list[VehicleSnapshot]:
    """Available vehicles sorted cheapest-first (deterministic)."""
    return sorted(
        [v for v in vehicles.values() if v.available and v.status == "available"],
        key=lambda v: (v.cost_per_km, v.id),
    )


def _repair_infeasibility(
    assignments: list[Assignment],
    deliveries: dict[int, DeliverySnapshot],
    vehicles: dict[int, VehicleSnapshot],
) -> list[Assignment]:
    """Deterministically fix capacity/availability violations.

    Returns a new list (does not mutate input).
    """
    # Copy
    current = [Assignment(a.delivery_id, a.vehicle_id) for a in assignments]
    eligible = _eligible_vehicles(vehicles)

    def _unavailable_vehicle_ids() -> set[int]:
        return {v.id for v in vehicles.values() if not v.available or v.status != "available"}

    # Pass 1 — move deliveries off unavailable vehicles
    bad_v = _unavailable_vehicle_ids()
    for a in current:
        if a.vehicle_id is None or a.vehicle_id not in bad_v:
            continue
        d = deliveries.get(a.delivery_id)
        if d is None:
            continue
        load = _loads(current, deliveries)
        best = None
        for v in eligible:
            if _spare_capacity(v, load) > 0:
                best = v.id
                break
        a.vehicle_id = best  # may remain None if nothing fits

    # Pass 2 — fix over-capacity vehicles by moving lowest-priority loads
    progress = True
    guard = 0
    while progress and guard < 100:
        progress = False
        guard += 1
        load = _loads(current, deliveries)
        for vid, n in list(load.items()):
            v = vehicles[vid]
            while n > v.capacity:
                # find the lowest-priority delivery on this vehicle to move
                on_v = [
                    a for a in current
                    if a.vehicle_id == vid and (
                        deliveries.get(a.delivery_id) is not None
                        and deliveries[a.delivery_id].status not in
                        ("delivered", "cancelled", "failed")
                    )
                ]
                if not on_v:
                    break
                on_v.sort(key=lambda a: (
                    PRIORITY_WEIGHT.get(deliveries[a.delivery_id].priority, 0.5),
                    a.delivery_id,
                ))
                candidate = on_v[0]

                # try to move to a vehicle with spare capacity
                target = None
                for v2 in eligible:
                    if v2.id == vid:
                        continue
                    if _spare_capacity(v2, load) > 0:
                        target = v2.id
                        break

                if target is None:
                    # no capacity anywhere — leave as is (still infeasible, honest)
                    break

                candidate.vehicle_id = target
                load[vid] = load.get(vid, 0) - 1
                load[target] = load.get(target, 0) + 1
                n = load[vid]
                progress = True
                if n <= v.capacity:
                    break

    return current


def _candidate_delivery_ids(
    current: list[Assignment],
    deliveries: dict[int, DeliverySnapshot],
    vehicles: dict[int, VehicleSnapshot],
    risk_scores: dict[int, float],
) -> list[int]:
    """Deliveries worth optimizing: at-risk, urgent+unassigned, or currently
    assigned to an unavailable vehicle."""
    bad_v = {v.id for v in vehicles.values() if not v.available or v.status != "available"}
    ids: set[int] = set()
    for a in current:
        d = deliveries.get(a.delivery_id)
        if d is None or d.status in ("delivered", "cancelled", "failed"):
            continue
        if risk_scores.get(d.id, 0.0) >= 50.0:
            ids.add(d.id)
        if d.priority in ("urgent", "high") and a.vehicle_id is None:
            ids.add(d.id)
        if a.vehicle_id in bad_v:
            ids.add(d.id)
    return sorted(ids)


def _build_plan(
    kind: str,
    weights: dict[str, float],
    deliveries: dict[int, DeliverySnapshot],
    vehicles: dict[int, VehicleSnapshot],
    risk_scores: dict[int, float],
) -> PlanResult:
    baseline = _baseline_assignments(deliveries)
    current = _repair_infeasibility(baseline, deliveries, vehicles)

    eligible = _eligible_vehicles(vehicles)
    candidates = _candidate_delivery_ids(current, deliveries, vehicles, risk_scores)

    for did in candidates:
        current_metrics = evaluate(current, baseline, deliveries, vehicles, weights)
        current_score = _objective_score(current_metrics, weights)
        current_vid = next((a.vehicle_id for a in current if a.delivery_id == did), None)

        best_vid = current_vid
        best_score = current_score

        # try each eligible vehicle
        for v in eligible:
            trial = [
                Assignment(a.delivery_id, v.id if a.delivery_id == did else a.vehicle_id)
                for a in current
            ]
            m = evaluate(trial, baseline, deliveries, vehicles, weights)
            if not m.feasible:
                continue
            s = _objective_score(m, weights)
            if s < best_score:
                best_score = s
                best_vid = v.id

        # try unassigning
        trial_unassign = [
            Assignment(a.delivery_id, None if a.delivery_id == did else a.vehicle_id)
            for a in current
        ]
        m_un = evaluate(trial_unassign, baseline, deliveries, vehicles, weights)
        if m_un.feasible:
            s_un = _objective_score(m_un, weights)
            if s_un < best_score:
                best_score = s_un
                best_vid = None

        # commit
        for a in current:
            if a.delivery_id == did:
                a.vehicle_id = best_vid
                break

    final_metrics = evaluate(current, baseline, deliveries, vehicles, weights)
    change_summary = _summarize_changes(baseline, current)

    explanation = (
        f"Plan kind={kind}. {change_summary} "
        f"Late deliveries={final_metrics.late_count}, "
        f"total delay={final_metrics.total_delay_minutes:.0f} min, "
        f"priority-weighted delay={final_metrics.priority_weighted_delay:.0f}, "
        f"extra cost={final_metrics.extra_cost:.2f}, "
        f"changes={final_metrics.changes}, "
        f"feasible={final_metrics.feasible}. "
        "Rule-based heuristic estimate, not a trained prediction."
    )

    return PlanResult(
        kind=kind,
        assignments=current,
        metrics=final_metrics,
        explanation=explanation,
    )


def _summarize_changes(baseline: list[Assignment], planned: list[Assignment]) -> str:
    base_map = {a.delivery_id: a.vehicle_id for a in baseline}
    n = sum(
        1 for a in planned
        if base_map.get(a.delivery_id) != a.vehicle_id
    )
    return f"{n} assignment(s) changed."


def generate_plans(
    deliveries: dict[int, DeliverySnapshot],
    vehicles: dict[int, VehicleSnapshot],
    risk_scores: dict[int, float],
) -> list[PlanResult]:
    baseline_assignments = _baseline_assignments(deliveries)
    baseline_metrics = evaluate(
        baseline_assignments, baseline_assignments, deliveries, vehicles, DEFAULT_WEIGHTS
    )
    baseline_result = PlanResult(
        kind="baseline",
        assignments=baseline_assignments,
        metrics=baseline_metrics,
        explanation=(
            "Baseline = current assignments, no changes. "
            f"Late={baseline_metrics.late_count}, "
            f"delay={baseline_metrics.total_delay_minutes:.0f} min, "
            f"feasible={baseline_metrics.feasible}."
        ),
    )

    minimize = _build_plan("minimize_delays", DEFAULT_WEIGHTS, deliveries, vehicles, risk_scores)
    balanced = _build_plan("balanced", BALANCED_WEIGHTS, deliveries, vehicles, risk_scores)
    return [baseline_result, minimize, balanced]


def compare(feasible_plans: list[PlanResult]) -> PlanResult:
    feasible = [p for p in feasible_plans if p.metrics.feasible]
    if not feasible:
        raise ValueError("No feasible plans to compare")
    return min(feasible, key=lambda p: _objective_score(p.metrics, DEFAULT_WEIGHTS))
