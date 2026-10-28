"""Operations Copilot (Module F).

Two modes:
- Fallback (deterministic): build answers directly from DB queries.
- LLM-enhanced: when GEMINI_API_KEY set, use Gemini to rephrase the answer
  naturally. Any failure → falls back to deterministic answer.

The LLM NEVER receives arbitrary DB rows. It receives a curated, JSON-safe
summary of the query result. It cannot invent delivery IDs — the fallback
answer already contains the true IDs; we only allow the model to rewrite prose.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.integrations.llm_client import get_llm_provider
from app.models.delivery import Delivery, DeliveryPriority, DeliveryStatus
from app.models.incident import Incident, IncidentStatus
from app.models.vehicle import Vehicle, VehicleStatus


ACTIVE = (DeliveryStatus.PENDING, DeliveryStatus.ASSIGNED,
          DeliveryStatus.IN_TRANSIT, DeliveryStatus.DELAYED)


@dataclass
class CopilotAnswer:
    question: str
    answer: str
    source: str  # "llm" | "fallback"
    tool_used: str
    facts: dict[str, Any]

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "source": self.source,
            "tool_used": self.tool_used,
            "facts": self.facts,
        }


def _deliveries_at_risk(db: Session, limit: int = 10) -> list[Delivery]:
    return (
        db.query(Delivery)
        .filter(Delivery.status.in_(ACTIVE), Delivery.risk_score >= 50.0)
        .order_by(desc(Delivery.risk_score))
        .limit(limit)
        .all()
    )


def _top_incidents(db: Session, limit: int = 5) -> list[Incident]:
    return (
        db.query(Incident)
        .filter(Incident.status == IncidentStatus.OPEN)
        .order_by(desc(Incident.severity), desc(Incident.created_at))
        .limit(limit)
        .all()
    )


def _deliveries_by_priority(db: Session, limit: int = 10) -> list[Delivery]:
    return (
        db.query(Delivery)
        .filter(Delivery.status.in_(ACTIVE),
                Delivery.priority.in_([DeliveryPriority.URGENT, DeliveryPriority.HIGH]))
        .order_by(desc(Delivery.risk_score), Delivery.promised_deadline.asc())
        .limit(limit)
        .all()
    )


def _situation_summary(db: Session) -> dict:
    total = db.query(func.count(Delivery.id)).filter(Delivery.status.in_(ACTIVE)).scalar() or 0
    at_risk = db.query(func.count(Delivery.id)).filter(
        Delivery.status.in_(ACTIVE), Delivery.risk_score >= 50.0
    ).scalar() or 0
    open_inc = db.query(func.count(Incident.id)).filter(
        Incident.status == IncidentStatus.OPEN
    ).scalar() or 0
    avail_vehicles = db.query(func.count(Vehicle.id)).filter(
        Vehicle.available == True, Vehicle.status == VehicleStatus.AVAILABLE  # noqa: E712
    ).scalar() or 0
    unassigned_urgent = db.query(func.count(Delivery.id)).filter(
        Delivery.status == DeliveryStatus.PENDING,
        Delivery.vehicle_id.is_(None),
        Delivery.priority.in_([DeliveryPriority.URGENT, DeliveryPriority.HIGH]),
    ).scalar() or 0
    return {
        "active_deliveries": total,
        "deliveries_at_risk": at_risk,
        "open_incidents": open_inc,
        "available_vehicles": avail_vehicles,
        "unassigned_high_priority": unassigned_urgent,
    }


# ---------- Deterministic answers ----------

def _deterministic_at_risk(db: Session) -> CopilotAnswer:
    rows = _deliveries_at_risk(db)
    facts = {
        "count": len(rows),
        "deliveries": [
            {"id": d.id, "tracking_number": d.tracking_number,
             "risk_score": d.risk_score, "priority": d.priority.value}
            for d in rows
        ],
    }
    if not rows:
        answer = "No deliveries are currently at elevated risk (risk score >= 50)."
    else:
        bullets = "\n".join(
            f"- {d.tracking_number} (id {d.id}): risk {d.risk_score:.0f}/100, "
            f"{d.priority.value} priority"
            for d in rows
        )
        answer = f"{len(rows)} deliveries are at elevated risk:\n{bullets}"
    return CopilotAnswer(
        question="Which deliveries are most likely to be late?",
        answer=answer, source="fallback",
        tool_used="deliveries_at_risk", facts=facts,
    )


def _deterministic_priorities(db: Session) -> CopilotAnswer:
    rows = _deliveries_by_priority(db)
    facts = {
        "count": len(rows),
        "deliveries": [
            {"id": d.id, "tracking_number": d.tracking_number,
             "priority": d.priority.value, "risk_score": d.risk_score,
             "deadline": d.promised_deadline.isoformat() if d.promised_deadline else None}
            for d in rows
        ],
    }
    if not rows:
        answer = "No high or urgent priority deliveries are currently active."
    else:
        bullets = "\n".join(
            f"- {d.tracking_number} ({d.priority.value}) — risk {d.risk_score:.0f}, "
            f"deadline {d.promised_deadline.isoformat() if d.promised_deadline else 'n/a'}"
            for d in rows
        )
        answer = f"Prioritize these {len(rows)} high/urgent deliveries:\n{bullets}"
    return CopilotAnswer(
        question="Which deliveries should be prioritized?",
        answer=answer, source="fallback",
        tool_used="priority_deliveries", facts=facts,
    )


def _deterministic_summary(db: Session) -> CopilotAnswer:
    s = _situation_summary(db)
    top = _top_incidents(db)
    incidents = [
        {"id": i.id, "kind": i.kind, "severity": i.severity.value, "title": i.title}
        for i in top
    ]
    answer = (
        f"Current situation: {s['active_deliveries']} active deliveries, "
        f"{s['deliveries_at_risk']} at risk (score >= 50), "
        f"{s['open_incidents']} open incidents, "
        f"{s['available_vehicles']} vehicles available, "
        f"{s['unassigned_high_priority']} unassigned high-priority deliveries."
    )
    if incidents:
        answer += "\n\nTop incidents:\n" + "\n".join(
            f"- [{i['severity']}] {i['title']}" for i in incidents
        )
    return CopilotAnswer(
        question="Summarize the current operational situation.",
        answer=answer, source="fallback",
        tool_used="situation_summary",
        facts={"summary": s, "top_incidents": incidents},
    )


def _deterministic_biggest_risk(db: Session) -> CopilotAnswer:
    top = _top_incidents(db, limit=1)
    if not top:
        s = _situation_summary(db)
        answer = (
            "No open incidents right now. "
            f"{s['deliveries_at_risk']} deliveries are still above the risk threshold."
        )
        facts = {"summary": s}
    else:
        inc = top[0]
        answer = (
            f"The single biggest operational risk right now is '{inc.title}' "
            f"(severity: {inc.severity.value}). {inc.description}\n"
            f"Suggested action: {inc.suggested_action}"
        )
        facts = {"incident": {
            "id": inc.id, "kind": inc.kind, "severity": inc.severity.value,
            "title": inc.title, "description": inc.description,
        }}
    return CopilotAnswer(
        question="What is causing today's largest operational risk?",
        answer=answer, source="fallback",
        tool_used="biggest_risk", facts=facts,
    )


# ---------- Routing ----------

def _route(question: str) -> str:
    q = question.lower()
    if "summar" in q or "situation" in q or "overview" in q:
        return "situation_summary"
    if "priorit" in q:
        return "priority_deliveries"
    if "risk" in q and ("cause" in q or "biggest" in q or "largest" in q or "why" in q):
        return "biggest_risk"
    if "late" in q or "risk" in q:
        return "deliveries_at_risk"
    return "situation_summary"


def _maybe_enhance_with_llm(answer: CopilotAnswer, fallback_available: bool) -> CopilotAnswer:
    """Attempt to naturalize the answer with the LLM. Never trusts LLM for facts."""
    provider = get_llm_provider()
    if not provider.available:
        if fallback_available:
            answer.answer += "\n\n(Note: AI rephrasing is disabled — GEMINI_API_KEY is not set. "
            answer.answer += "Answers are generated deterministically from current data.)"
        return answer

    prompt = (
        "You are an operations assistant for a logistics dashboard. "
        "Rewrite the following answer in clear, calm, professional prose for an operations manager. "
        "Do NOT invent delivery IDs, vehicle codes, or facts. Only rephrase what is given. "
        "Keep all numeric values exactly as provided.\n\n"
        f"Facts: {json.dumps(answer.facts)}\n\n"
        f"Deterministic answer: {answer.answer}\n\n"
        "Rewritten answer (plain text, concise, no markdown headers):"
    )
    rewritten = provider.generate_text(prompt, max_tokens=350)
    if rewritten:
        answer.answer = rewritten
        answer.source = "llm"
    return answer


def query(db: Session, question: str) -> CopilotAnswer:
    route = _route(question)
    if route == "deliveries_at_risk":
        base = _deterministic_at_risk(db)
    elif route == "priority_deliveries":
        base = _deterministic_priorities(db)
    elif route == "biggest_risk":
        base = _deterministic_biggest_risk(db)
    else:
        base = _deterministic_summary(db)
    base.question = question
    return _maybe_enhance_with_llm(base, fallback_available=True)
