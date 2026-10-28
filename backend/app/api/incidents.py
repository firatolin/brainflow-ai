from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import Pagination, pagination_params
from app.models.incident import Incident, IncidentSeverity, IncidentStatus
from app.schemas.common import Page
from app.schemas.incident import IncidentRead, IncidentUpdate
from app.schemas.scan import ScanRunRead
from app.services import scan_service


router = APIRouter(prefix="/incidents", tags=["incidents"])


SORTABLE = {
    "id": Incident.id,
    "severity": Incident.severity,
    "created_at": Incident.created_at,
    "updated_at": Incident.updated_at,
}


@router.get("", response_model=Page[IncidentRead])
def list_incidents(
    db: Session = Depends(get_db),
    pg: Pagination = Depends(pagination_params),
    status_filter: IncidentStatus | None = Query(default=None, alias="status"),
    severity: IncidentSeverity | None = Query(default=None),
    kind: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    sort: str = Query(default="created_at"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
):
    if sort not in SORTABLE:
        raise HTTPException(400, f"Invalid sort field. Allowed: {sorted(SORTABLE)}")
    q = db.query(Incident)
    if status_filter:
        q = q.filter(Incident.status == status_filter)
    if severity:
        q = q.filter(Incident.severity == severity)
    if kind:
        q = q.filter(Incident.kind == kind)
    if entity_type:
        q = q.filter(Incident.entity_type == entity_type)
    total = q.count()
    col = SORTABLE[sort]
    items = q.order_by(col.asc() if order == "asc" else col.desc()).offset(pg.offset).limit(pg.page_size).all()
    pages = (total + pg.page_size - 1) // pg.page_size if total else 0
    return Page[IncidentRead](items=items, total=total, page=pg.page, page_size=pg.page_size, pages=pages)


@router.post("/scan", response_model=ScanRunRead)
def trigger_scan(db: Session = Depends(get_db)):
    run = scan_service.run_scan(db, triggered_by="manual")
    return run


@router.patch("/{incident_id}", response_model=IncidentRead)
def update_incident(incident_id: int, payload: IncidentUpdate, db: Session = Depends(get_db)):
    inc = db.get(Incident, incident_id)
    if not inc:
        raise HTTPException(404, "Incident not found")
    now = datetime.now(timezone.utc)
    if payload.status == IncidentStatus.ACKNOWLEDGED:
        inc.status = IncidentStatus.ACKNOWLEDGED
        inc.acknowledged_at = inc.acknowledged_at or now
    elif payload.status == IncidentStatus.RESOLVED:
        inc.status = IncidentStatus.RESOLVED
        inc.resolved_at = inc.resolved_at or now
        inc.resolution_note = payload.resolution_note or inc.resolution_note or "manually resolved"
    elif payload.status == IncidentStatus.OPEN:
        inc.status = IncidentStatus.OPEN
        inc.resolved_at = None
        inc.resolution_note = None
    else:
        raise HTTPException(400, "Unsupported status")
    db.commit()
    db.refresh(inc)
    return inc
