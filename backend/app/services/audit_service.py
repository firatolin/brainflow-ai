"""Append-only audit trail. Never mutates existing rows."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent


def record(
    db: Session,
    event_type: str,
    *,
    entity_type: str | None = None,
    entity_id: int | None = None,
    actor: str = "system",
    context: dict[str, Any] | None = None,
) -> AuditEvent:
    ev = AuditEvent(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor=actor,
        context_json=json.dumps(context or {}, default=str),
    )
    db.add(ev)
    db.flush()
    return ev
