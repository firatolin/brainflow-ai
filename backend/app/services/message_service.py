"""Customer message drafts (Module J).

All drafts require human review — never sent automatically.
LLM used for natural phrasing when configured; deterministic template otherwise.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.integrations.llm_client import get_llm_provider
from app.models.delivery import Delivery


@dataclass
class Draft:
    delivery_id: int
    tracking_number: str
    recipient_category: str
    reason: str
    body: str
    source: str  # "llm" | "template"
    facts: dict[str, Any]
    reviewed: bool = False

    def to_dict(self) -> dict:
        return {
            "delivery_id": self.delivery_id,
            "tracking_number": self.tracking_number,
            "recipient_category": self.recipient_category,
            "reason": self.reason,
            "body": self.body,
            "source": self.source,
            "facts": self.facts,
            "reviewed": self.reviewed,
            "status": "draft",
            "requires_human_review": True,
        }


def _template_body(delivery: Delivery, reason: str) -> str:
    deadline = delivery.promised_deadline.isoformat() if delivery.promised_deadline else "soon"
    return (
        f"Hello,\n\n"
        f"We're writing about your delivery {delivery.tracking_number} "
        f"to {delivery.destination}.\n\n"
        f"{reason}\n\n"
        f"Your current promised window: {deadline}.\n\n"
        f"Our operations team is actively monitoring your delivery and will "
        f"follow up with any update.\n\n"
        f"Thank you for your patience,\n"
        f"BrainFlow Logistics Operations"
    )


def _reason_from_delivery(delivery: Delivery) -> str:
    if delivery.status.value == "delayed":
        return "Your delivery is currently running behind schedule due to operational conditions."
    if delivery.risk_score >= 75:
        return "We are proactively reaching out because this delivery may be delayed."
    if delivery.risk_score >= 50:
        return "We're monitoring a potential delay on your delivery and want to keep you informed."
    return "This is a proactive status update on your delivery."


def create_draft(db: Session, delivery_id: int) -> Draft | None:
    delivery = db.get(Delivery, delivery_id)
    if delivery is None:
        return None

    reason = _reason_from_delivery(delivery)
    template = _template_body(delivery, reason)
    facts = {
        "tracking_number": delivery.tracking_number,
        "destination": delivery.destination,
        "status": delivery.status.value,
        "risk_score": delivery.risk_score,
        "deadline": delivery.promised_deadline.isoformat() if delivery.promised_deadline else None,
    }

    provider = get_llm_provider()
    if provider.available:
        prompt = (
            "Write a short, polite customer-facing status update (plain text, no markdown). "
            "Do NOT invent facts. Use only the following facts. Sign as 'BrainFlow Logistics Operations'.\n\n"
            f"Facts: {facts}\n\n"
            f"Draft template to polish:\n{template}\n\n"
            "Polished version:"
        )
        rewritten = provider.generate_text(prompt, max_tokens=250)
        if rewritten:
            return Draft(
                delivery_id=delivery.id,
                tracking_number=delivery.tracking_number,
                recipient_category="customer",
                reason=reason,
                body=rewritten,
                source="llm",
                facts=facts,
            )

    return Draft(
        delivery_id=delivery.id,
        tracking_number=delivery.tracking_number,
        recipient_category="customer",
        reason=reason,
        body=template,
        source="template",
        facts=facts,
    )
