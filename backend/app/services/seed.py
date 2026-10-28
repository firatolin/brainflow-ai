"""Deterministic seed data for BrainFlow AI demo.

Creates 6 vehicles and 40 deliveries across zones, with a scenario designed
to exercise: rain exposure, an unavailable vehicle, two urgent deliveries,
capacity pressure on a small-capacity vehicle, and a spread of risk/priority.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.delivery import Delivery, DeliveryPriority, DeliveryStatus
from app.models.vehicle import Vehicle, VehicleStatus, VehicleType


ZONES = ["central", "north", "south", "east", "west", "airport"]
DESTINATIONS = [
    "Bole Distribution Center",
    "Megenagna Retail Hub",
    "Piassa Merchant Row",
    "Gerji Fulfillment Yard",
    "CMC Logistics Dock",
    "Sarbet Market Point",
    "Merkato Wholesale",
    "Ayat Residential Block",
    "Kality Industrial Park",
    "Summit Commercial Plaza",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def seed_database(db: Session, *, reset: bool = True) -> dict:
    """Seed vehicles + deliveries. If reset=True, existing data is removed first."""
    if reset:
        db.query(Delivery).delete()
        db.query(Vehicle).delete()
        db.commit()

    rng = random.Random(42)  # deterministic

    # ----- Vehicles -----
    vehicles_data = [
        dict(code="VAN-01", vehicle_type=VehicleType.VAN,      capacity=8,  location_zone="central",  available=True,  status=VehicleStatus.AVAILABLE, cost_per_km=1.2),
        dict(code="VAN-02", vehicle_type=VehicleType.VAN,      capacity=8,  location_zone="north",    available=True,  status=VehicleStatus.AVAILABLE, cost_per_km=1.2),
        dict(code="TRK-01", vehicle_type=VehicleType.TRUCK,    capacity=20, location_zone="south",    available=True,  status=VehicleStatus.AVAILABLE, cost_per_km=2.4),
        dict(code="MBK-01", vehicle_type=VehicleType.MOTORBIKE,capacity=2,  location_zone="central",  available=True,  status=VehicleStatus.AVAILABLE, cost_per_km=0.5),
        # The scenario vehicle that becomes unavailable
        dict(code="VAN-03", vehicle_type=VehicleType.VAN,      capacity=6,  location_zone="east",     available=False, status=VehicleStatus.MAINTENANCE, cost_per_km=1.3),
        dict(code="CAR-01", vehicle_type=VehicleType.CAR,      capacity=4,  location_zone="airport",  available=True,  status=VehicleStatus.AVAILABLE, cost_per_km=1.0),
    ]
    vehicles = [Vehicle(**v) for v in vehicles_data]
    db.add_all(vehicles)
    db.flush()  # populate ids

    # ----- Deliveries -----
    now = _utcnow()
    deliveries: list[Delivery] = []
    # assignable vehicles = available ones
    assignable = [v for v in vehicles if v.available]

    # 2 urgent deliveries (highest priority) — one assigned, one pending (needs attention)
    urgent_specs = [
        dict(priority=DeliveryPriority.URGENT, deadline_in_hours=3,  weather=0.35, assign_to="VAN-01"),
        dict(priority=DeliveryPriority.URGENT, deadline_in_hours=4,  weather=0.15, assign_to=None),
    ]

    for idx, spec in enumerate(urgent_specs, start=1):
        dispatch = now - timedelta(minutes=30)
        deadline = now + timedelta(hours=spec["deadline_in_hours"])
        assign_code = spec["assign_to"]
        vehicle = next((v for v in vehicles if v.code == assign_code), None)
        d = Delivery(
            tracking_number=f"BF-URG-{idx:03d}",
            customer_ref=f"Urgent Client #{idx}",
            origin="Main Warehouse",
            destination=DESTINATIONS[(idx * 3) % len(DESTINATIONS)],
            scheduled_dispatch=dispatch,
            promised_deadline=deadline,
            priority=spec["priority"],
            status=DeliveryStatus.ASSIGNED if vehicle else DeliveryStatus.PENDING,
            vehicle_id=vehicle.id if vehicle else None,
            distance_km=round(rng.uniform(5, 25), 1),
            cost_estimate=round(rng.uniform(20, 80), 2),
            weather_exposure=spec["weather"],
        )
        deliveries.append(d)

    # 38 normal deliveries
    for i in range(38):
        deadline_in = rng.choice([2, 4, 6, 8, 12, 24, 36])
        dispatch = now - timedelta(minutes=rng.randint(0, 180))
        deadline = now + timedelta(hours=deadline_in)
        priority = rng.choices(
            [DeliveryPriority.LOW, DeliveryPriority.NORMAL, DeliveryPriority.HIGH],
            weights=[2, 6, 2],
        )[0]
        # assign ~60% to available vehicles
        vehicle = rng.choice(assignable) if rng.random() < 0.6 else None
        status = DeliveryStatus.ASSIGNED if vehicle else DeliveryStatus.PENDING
        d = Delivery(
            tracking_number=f"BF-{i + 1:05d}",
            customer_ref=f"Customer {i + 1:03d}",
            origin="Main Warehouse",
            destination=DESTINATIONS[i % len(DESTINATIONS)],
            scheduled_dispatch=dispatch,
            promised_deadline=deadline,
            priority=priority,
            status=status,
            vehicle_id=vehicle.id if vehicle else None,
            distance_km=round(rng.uniform(2, 40), 1),
            cost_estimate=round(rng.uniform(10, 120), 2),
            weather_exposure=round(rng.uniform(0.0, 0.6), 2),
        )
        deliveries.append(d)

    # A couple of completed deliveries for analytics realism
    for j in range(3):
        dispatch = now - timedelta(hours=8 + j)
        deadline = now - timedelta(hours=6 + j)
        arrival = now - timedelta(hours=6 + j, minutes=-rng.randint(0, 30))
        deliveries.append(
            Delivery(
                tracking_number=f"BF-DONE-{j + 1:03d}",
                customer_ref=f"Customer DONE-{j + 1:03d}",
                origin="Main Warehouse",
                destination=DESTINATIONS[(j + 5) % len(DESTINATIONS)],
                scheduled_dispatch=dispatch,
                promised_deadline=deadline,
                priority=DeliveryPriority.NORMAL,
                status=DeliveryStatus.DELIVERED,
                vehicle_id=vehicles[0].id,
                distance_km=round(rng.uniform(5, 20), 1),
                cost_estimate=round(rng.uniform(20, 60), 2),
                weather_exposure=0.1,
                actual_arrival=arrival,
            )
        )

    db.add_all(deliveries)
    db.commit()

    return {
        "vehicles": len(vehicles),
        "deliveries": len(deliveries),
        "unavailable_vehicles": [v.code for v in vehicles if not v.available],
        "urgent_deliveries": [d.tracking_number for d in deliveries if d.priority == DeliveryPriority.URGENT],
    }
