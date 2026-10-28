"""Deterministic rule-based risk estimator.

IMPORTANT: This is a rule-based estimate, not a trained statistical model.
All calculations are pure and reproducible; given identical inputs, the
engine returns identical scores.

Score (0..100) is the weighted sum of five normalised factors:

    factor                 weight   meaning
    ---------------------- -------  --------------------------------------------
    deadline_pressure       0.35    time left vs. estimated travel time
    current_delay           0.20    already off-schedule before dispatch
    priority_weight         0.15    urgent/high priority increases stakes
    weather_exposure        0.15    input weather_exposure (0..1)
    data_quality            0.15    missing / stale inputs raise uncertainty

Confidence (0..1) reflects data completeness:
    - missing vehicle             -0.25
    - missing scheduled_dispatch  -0.15
    - no estimated_arrival        -0.15
    - risk inputs stale > 6h      -0.20
    Confidence floor = 0.2

Category bands:
    0-24   low
    25-49  medium
    50-74  high
    75-100 critical
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from app.models.delivery import Delivery, DeliveryPriority, DeliveryStatus
from app.models.vehicle import Vehicle


PRIORITY_WEIGHT: dict[DeliveryPriority, float] = {
    DeliveryPriority.LOW: 0.10,
    DeliveryPriority.NORMAL: 0.30,
    DeliveryPriority.HIGH: 0.65,
    DeliveryPriority.URGENT: 1.00,
}

# Assumed average speed when we have to fall back to a heuristic travel time.
DEFAULT_AVG_SPEED_KMH = 25.0


@dataclass
class RiskResult:
    delivery_id: int
    score: float
    category: str
    confidence: float
    intervention: str
    factors: list[dict[str, Any]] = field(default_factory=list)
    assessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["assessed_at"] = self.assessed_at.isoformat()
        return d


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _deadline_pressure_factor(delivery: Delivery, now: datetime) -> tuple[float, dict]:
    """0..1. 0 = plenty of time, 1 = already past deadline."""
    deadline = _as_aware(delivery.promised_deadline)
    if deadline is None:
        return 0.6, {"name": "deadline_pressure", "value": 0.6,
                     "reason": "missing deadline (assumed risky)"}

    # estimated travel minutes -> from distance / DEFAULT_AVG_SPEED_KMH
    distance = max(delivery.distance_km or 0.0, 0.5)
    eta_minutes = max((distance / DEFAULT_AVG_SPEED_KMH) * 60.0, 5.0)

    minutes_left = (deadline - now).total_seconds() / 60.0
    if minutes_left <= 0:
        return 1.0, {"name": "deadline_pressure", "value": 1.0,
                     "reason": f"past deadline by {-minutes_left:.0f} min"}

    ratio = minutes_left / eta_minutes
    # ratio >= 3 -> 0 ; ratio <= 0.5 -> 1 ; linear between
    raw = max(0.0, min(1.0, 1.0 - (ratio - 0.5) / 2.5))
    return raw, {
        "name": "deadline_pressure",
        "value": round(raw, 3),
        "minutes_left": round(minutes_left, 1),
        "eta_minutes": round(eta_minutes, 1),
    }


def _current_delay_factor(delivery: Delivery, now: datetime) -> tuple[float, dict]:
    """0..1. Positive if now > scheduled dispatch + expected travel."""
    dispatch = _as_aware(delivery.scheduled_dispatch)
    if dispatch is None:
        return 0.3, {"name": "current_delay", "value": 0.3,
                     "reason": "missing scheduled_dispatch"}

    distance = max(delivery.distance_km or 0.0, 0.5)
    eta_minutes = max((distance / DEFAULT_AVG_SPEED_KMH) * 60.0, 5.0)
    expected_arrival = dispatch + timedelta(minutes=eta_minutes)
    delay_minutes = (now - expected_arrival).total_seconds() / 60.0

    if delay_minutes <= 0:
        return 0.0, {"name": "current_delay", "value": 0.0,
                     "delay_minutes": round(delay_minutes, 1)}
    raw = min(1.0, delay_minutes / 120.0)  # 2h late = 1.0
    return raw, {"name": "current_delay", "value": round(raw, 3),
                 "delay_minutes": round(delay_minutes, 1)}


def _weather_factor(delivery: Delivery) -> tuple[float, dict]:
    we = delivery.weather_exposure or 0.0
    we = max(0.0, min(1.0, we))
    return we, {"name": "weather_exposure", "value": round(we, 3)}


def _priority_factor(delivery: Delivery) -> tuple[float, dict]:
    w = PRIORITY_WEIGHT.get(delivery.priority, 0.3)
    return w, {"name": "priority_weight", "value": round(w, 3),
               "priority": delivery.priority.value}


def _data_quality(delivery: Delivery, vehicle: Vehicle | None, now: datetime) -> tuple[float, dict]:
    """Returns (confidence 0..1, factor breakdown)."""
    conf = 1.0
    issues: list[str] = []
    if vehicle is None and delivery.status not in (
        DeliveryStatus.DELIVERED, DeliveryStatus.FAILED, DeliveryStatus.CANCELLED
    ):
        conf -= 0.25
        issues.append("no_vehicle")
    if delivery.scheduled_dispatch is None:
        conf -= 0.15
        issues.append("no_scheduled_dispatch")
    if delivery.estimated_arrival is None:
        conf -= 0.15
        issues.append("no_estimated_arrival")
    updated = _as_aware(delivery.updated_at)
    if updated and (now - updated) > timedelta(hours=6):
        conf -= 0.20
        issues.append("stale_estimate")
    conf = max(0.2, round(conf, 3))
    # higher confidence = lower risk from data quality; invert
    inverse = round(1.0 - conf, 3)
    return inverse, {
        "name": "data_quality",
        "value": inverse,
        "confidence": conf,
        "issues": issues,
    }


def _categorize(score: float) -> str:
    if score < 25:
        return "low"
    if score < 50:
        return "medium"
    if score < 75:
        return "high"
    return "critical"


def _intervention(score: float, delivery: Delivery) -> str:
    if delivery.status in (DeliveryStatus.DELIVERED, DeliveryStatus.CANCELLED):
        return "none"
    if delivery.status == DeliveryStatus.FAILED:
        return "escalate"
    if score >= 75:
        return "reassign_or_escalate"
    if score >= 50:
        return "prioritize"
    if score >= 25:
        return "monitor"
    return "none"


def assess(delivery: Delivery, vehicle: Vehicle | None, *, now: datetime | None = None) -> RiskResult:
    now = now or _now()

    deadline_raw, deadline_f = _deadline_pressure_factor(delivery, now)
    delay_raw, delay_f = _current_delay_factor(delivery, now)
    weather_raw, weather_f = _weather_factor(delivery)
    priority_raw, priority_f = _priority_factor(delivery)
    quality_raw, quality_f = _data_quality(delivery, vehicle, now)

    weighted = (
        0.35 * deadline_raw
        + 0.20 * delay_raw
        + 0.15 * weather_raw
        + 0.15 * priority_raw
        + 0.15 * quality_raw
    )
    score = round(max(0.0, min(1.0, weighted)) * 100.0, 2)

    confidence = float(quality_f["confidence"])

    return RiskResult(
        delivery_id=delivery.id,
        score=score,
        category=_categorize(score),
        confidence=confidence,
        intervention=_intervention(score, delivery),
        factors=[deadline_f, delay_f, weather_f, priority_f, quality_f],
        assessed_at=now,
    )
