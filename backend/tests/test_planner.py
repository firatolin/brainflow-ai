import time
from app.services.optimizer.plan_types import DeliverySnapshot, VehicleSnapshot
from app.services.optimizer.planner import generate_plans


def _d(i, priority="normal", vehicle_id=None, status="pending",
       dist=10.0, deadline_offset=3600, weather=0.0):
    now = time.time()
    return DeliverySnapshot(
        id=i, priority=priority, status=status, vehicle_id=vehicle_id,
        distance_km=dist, deadline_ts=now + deadline_offset,
        dispatch_ts=now, weather_exposure=weather,
    )


def _v(i, code="V", cap=5, avail=True, status="available", cost=1.0):
    return VehicleSnapshot(id=i, code=code, capacity=cap, available=avail,
                           status=status, cost_per_km=cost)


def test_baseline_plan_no_changes():
    deliveries = {1: _d(1, vehicle_id=1), 2: _d(2, vehicle_id=1)}
    vehicles = {1: _v(1)}
    risks = {1: 0.0, 2: 0.0}
    plans = generate_plans(deliveries, vehicles, risks)
    baseline = next(p for p in plans if p.kind == "baseline")
    assert baseline.metrics.changes == 0


def test_three_plans_returned():
    deliveries = {1: _d(1, vehicle_id=1)}
    vehicles = {1: _v(1)}
    plans = generate_plans(deliveries, vehicles, {1: 0.0})
    kinds = {p.kind for p in plans}
    assert kinds == {"baseline", "minimize_delays", "balanced"}


def test_determinism_same_inputs_same_plan():
    deliveries = {1: _d(1, priority="urgent", vehicle_id=1),
                  2: _d(2, vehicle_id=1, deadline_offset=1800)}
    vehicles = {1: _v(1, cap=2), 2: _v(2, code="V2")}
    risks = {1: 80.0, 2: 20.0}
    p1 = generate_plans(deliveries, vehicles, risks)
    p2 = generate_plans(deliveries, vehicles, risks)
    m1 = next(p for p in p1 if p.kind == "minimize_delays").metrics
    m2 = next(p for p in p2 if p.kind == "minimize_delays").metrics
    assert m1.late_count == m2.late_count
    assert m1.changes == m2.changes
    assert m1.total_delay_minutes == m2.total_delay_minutes


def test_capacity_respected():
    # 1 vehicle with cap=1, two urgent deliveries assigned to it — planner must respect cap
    deliveries = {
        1: _d(1, priority="urgent", vehicle_id=1, deadline_offset=3600),
        2: _d(2, priority="urgent", vehicle_id=1, deadline_offset=3600),
    }
    vehicles = {1: _v(1, cap=1), 2: _v(2, code="V2", cap=5)}
    plans = generate_plans(deliveries, vehicles, {1: 60.0, 2: 60.0})
    for p in plans:
        if p.metrics.feasible:
            # count per vehicle from assignments
            loads = {}
            for a in p.assignments:
                if a.vehicle_id is None: continue
                loads[a.vehicle_id] = loads.get(a.vehicle_id, 0) + 1
            for vid, n in loads.items():
                assert n <= vehicles[vid].capacity, f"plan {p.kind} broke capacity for v{vid}"
                break


def test_unassigned_urgent_gets_assigned():
    deliveries = {1: _d(1, priority="urgent", vehicle_id=None, deadline_offset=3600)}
    vehicles = {1: _v(1)}
    plans = generate_plans(deliveries, vehicles, {1: 60.0})
    minimize = next(p for p in plans if p.kind == "minimize_delays")
    assigned = next((a for a in minimize.assignments if a.delivery_id == 1), None)
    assert assigned is not None
    assert assigned.vehicle_id == 1


def test_planner_repairs_capacity_overflow():
    """4 deliveries on a capacity-2 vehicle; another vehicle has room."""
    deliveries = {
        1: _d(1, vehicle_id=1, priority="high"),
        2: _d(2, vehicle_id=1, priority="high"),
        3: _d(3, vehicle_id=1, priority="normal"),
        4: _d(4, vehicle_id=1, priority="low"),
    }
    vehicles = {1: _v(1, cap=2), 2: _v(2, code="V2", cap=10)}
    plans = generate_plans(deliveries, vehicles, {i: 0.0 for i in range(1, 5)})
    minimize = next(p for p in plans if p.kind == "minimize_delays")
    assert minimize.metrics.feasible is True, minimize.metrics.infeasibility_reasons
    # count per vehicle
    loads = {}
    for a in minimize.assignments:
        if a.vehicle_id is None:
            continue
        loads[a.vehicle_id] = loads.get(a.vehicle_id, 0) + 1
    for vid, n in loads.items():
        assert n <= vehicles[vid].capacity


def test_planner_repairs_unavailable_vehicle():
    deliveries = {
        1: _d(1, vehicle_id=1),
        2: _d(2, vehicle_id=1),
    }
    vehicles = {
        1: _v(1, cap=5, avail=False, status="maintenance"),
        2: _v(2, code="V2", cap=5),
    }
    plans = generate_plans(deliveries, vehicles, {1: 0.0, 2: 0.0})
    minimize = next(p for p in plans if p.kind == "minimize_delays")
    assert minimize.metrics.feasible is True
    assert all(a.vehicle_id != 1 for a in minimize.assignments)
