from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.models.delivery import Delivery, DeliveryStatus
from app.models.delivery_history import DeliveryHistory
from app.models.vehicle import Vehicle, VehicleStatus


# ---------- State machine ----------
# Valid transitions for a delivery. Any missing key means "no transitions allowed".
ALLOWED_TRANSITIONS: dict[DeliveryStatus, set[DeliveryStatus]] = {
    DeliveryStatus.PENDING:     {DeliveryStatus.ASSIGNED, DeliveryStatus.CANCELLED},
    DeliveryStatus.ASSIGNED:    {DeliveryStatus.IN_TRANSIT, DeliveryStatus.PENDING, DeliveryStatus.CANCELLED},
    DeliveryStatus.IN_TRANSIT:  {DeliveryStatus.DELIVERED, DeliveryStatus.DELAYED, DeliveryStatus.FAILED},
    DeliveryStatus.DELAYED:     {DeliveryStatus.DELIVERED, DeliveryStatus.FAILED, DeliveryStatus.IN_TRANSIT},
    DeliveryStatus.DELIVERED:   set(),   # terminal
    DeliveryStatus.FAILED:      set(),   # terminal
    DeliveryStatus.CANCELLED:   set(),   # terminal
}


def is_valid_transition(current: DeliveryStatus, target: DeliveryStatus) -> bool:
    if current == target:
        return True
    return target in ALLOWED_TRANSITIONS.get(current, set())


def record_history(
    db: Session,
    delivery_id: int,
    event_type: str,
    *,
    from_status: DeliveryStatus | None = None,
    to_status: DeliveryStatus | None = None,
    from_vehicle_id: int | None = None,
    to_vehicle_id: int | None = None,
    note: str | None = None,
) -> None:
    db.add(
        DeliveryHistory(
            delivery_id=delivery_id,
            event_type=event_type,
            from_status=from_status.value if from_status else None,
            to_status=to_status.value if to_status else None,
            from_vehicle_id=from_vehicle_id,
            to_vehicle_id=to_vehicle_id,
            note=note,
        )
    )


def _load_vehicle(db: Session, vehicle_id: int) -> Vehicle:
    v = db.get(Vehicle, vehicle_id)
    if not v:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return v


def _assert_vehicle_can_take_delivery(db: Session, vehicle: Vehicle, delivery: Delivery) -> None:
    if not vehicle.available or vehicle.status != VehicleStatus.AVAILABLE:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"Vehicle {vehicle.code} is not available for new assignments",
        )
    # capacity check: count currently active (non-terminal) deliveries assigned
    active = (
        db.query(Delivery)
        .filter(
            Delivery.vehicle_id == vehicle.id,
            Delivery.status.in_(
                [DeliveryStatus.ASSIGNED, DeliveryStatus.IN_TRANSIT, DeliveryStatus.DELAYED]
            ),
        )
        .count()
    )
    # if this delivery is already assigned to same vehicle, exclude it from count
    if delivery.vehicle_id == vehicle.id:
        active = max(active - 1, 0)
    if active >= vehicle.capacity:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"Vehicle {vehicle.code} at capacity ({active}/{vehicle.capacity})",
        )


# ---------- Public operations ----------

def create_delivery(db: Session, data: dict) -> Delivery:
    vehicle_id = data.pop("vehicle_id", None)
    if vehicle_id is not None:
        vehicle = _load_vehicle(db, vehicle_id)
        # Just record intent; capacity check happens after status set below
    delivery = Delivery(**data)
    if vehicle_id is not None:
        delivery.vehicle_id = vehicle_id
        delivery.status = DeliveryStatus.ASSIGNED
        _assert_vehicle_can_take_delivery(db, vehicle, delivery)
    else:
        delivery.status = DeliveryStatus.PENDING
    db.add(delivery)
    db.flush()
    record_history(
        db,
        delivery.id,
        event_type="created",
        to_status=delivery.status,
        to_vehicle_id=delivery.vehicle_id,
    )
    db.commit()
    db.refresh(delivery)
    return delivery


def update_delivery(db: Session, delivery_id: int, data: dict) -> Delivery:
    delivery = db.get(Delivery, delivery_id)
    if not delivery:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Delivery not found")

    before = {k: getattr(delivery, k) for k in data.keys() if hasattr(delivery, k)}
    for k, v in data.items():
        setattr(delivery, k, v)
    if data:
        record_history(db, delivery.id, event_type="updated", note=f"fields: {', '.join(data.keys())}")

    db.commit()
    db.refresh(delivery)
    return delivery


def assign_delivery(db: Session, delivery_id: int, vehicle_id: int | None) -> Delivery:
    delivery = db.get(Delivery, delivery_id)
    if not delivery:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Delivery not found")

    if delivery.status in (DeliveryStatus.DELIVERED, DeliveryStatus.FAILED, DeliveryStatus.CANCELLED):
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"Cannot reassign a delivery in terminal state '{delivery.status.value}'",
        )

    prev_vehicle_id = delivery.vehicle_id

    if vehicle_id is None:
        # unassign
        delivery.vehicle_id = None
        if delivery.status == DeliveryStatus.ASSIGNED:
            delivery.status = DeliveryStatus.PENDING
        record_history(
            db, delivery.id, "unassigned",
            from_vehicle_id=prev_vehicle_id, to_vehicle_id=None,
            from_status=DeliveryStatus.ASSIGNED, to_status=delivery.status,
        )
        db.commit()
        db.refresh(delivery)
        return delivery

    vehicle = _load_vehicle(db, vehicle_id)
    _assert_vehicle_can_take_delivery(db, vehicle, delivery)

    delivery.vehicle_id = vehicle.id
    if delivery.status == DeliveryStatus.PENDING:
        delivery.status = DeliveryStatus.ASSIGNED
    record_history(
        db, delivery.id, "assigned",
        from_vehicle_id=prev_vehicle_id, to_vehicle_id=vehicle.id,
        from_status=None, to_status=delivery.status,
    )
    db.commit()
    db.refresh(delivery)
    return delivery


def change_status(db: Session, delivery_id: int, target: DeliveryStatus, note: str | None = None) -> Delivery:
    delivery = db.get(Delivery, delivery_id)
    if not delivery:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Delivery not found")

    if not is_valid_transition(delivery.status, target):
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"Invalid transition: {delivery.status.value} -> {target.value}",
        )

    if target == DeliveryStatus.ASSIGNED and delivery.vehicle_id is None:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Cannot move to 'assigned' without a vehicle",
        )

    prev = delivery.status
    delivery.status = target
    if target == DeliveryStatus.DELIVERED and delivery.actual_arrival is None:
        delivery.actual_arrival = datetime.utcnow()

    record_history(
        db, delivery.id, "status_changed",
        from_status=prev, to_status=target, note=note,
    )
    db.commit()
    db.refresh(delivery)
    return delivery
