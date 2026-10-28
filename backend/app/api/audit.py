from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import Pagination, pagination_params
from app.models.audit_event import AuditEvent
from app.schemas.audit import AuditEventRead
from app.schemas.common import Page


router = APIRouter(prefix="/audit-events", tags=["audit"])


@router.get("", response_model=Page[AuditEventRead])
def list_audit_events(
    db: Session = Depends(get_db),
    pg: Pagination = Depends(pagination_params),
    event_type: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: int | None = Query(default=None),
    q: str | None = Query(default=None, description="search actor or context text"),
):
    query = db.query(AuditEvent)
    if event_type:
        query = query.filter(AuditEvent.event_type == event_type)
    if entity_type:
        query = query.filter(AuditEvent.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(AuditEvent.entity_id == entity_id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (AuditEvent.actor.ilike(like)) | (AuditEvent.context_json.ilike(like))
        )
    total = query.count()
    items = query.order_by(AuditEvent.id.desc()).offset(pg.offset).limit(pg.page_size).all()
    pages = (total + pg.page_size - 1) // pg.page_size if total else 0
    return Page[AuditEventRead](items=items, total=total, page=pg.page, page_size=pg.page_size, pages=pages)
