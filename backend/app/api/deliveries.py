from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import Pagination, pagination_params
from app.models.delivery import Delivery, DeliveryPriority, DeliveryStatus
from app.models.delivery_history import DeliveryHistory
from app.schemas.common import Page
from app.schemas.delivery import (
    DeliveryAssign,
    DeliveryCreate,
    DeliveryHistoryRead,
    DeliveryRead,
    DeliveryStatusChange,
    DeliveryUpdate,
)
from app.services import delivery_service


router = APIRouter(prefix="/deliveries", tags=["deliveries"])


SORTABLE = {
    "id": Delivery.id,
    "tracking_number": Delivery.tracking_number,
    "priority": Delivery.priority,
    "status": Delivery.status,
    "promised_deadline": Delivery.promised_deadline,
    "risk_score": Delivery.risk_score,
    "created_at": Delivery.created_at,
}


@router.get("", response_model=Page[DeliveryRead])
def list_deliveries(
    db: Session = Depends(get_db),
    pg: Pagination = Depends(pagination_params),
    status_filter: DeliveryStatus | None = Query(default=None, alias="status"),
    priority: DeliveryPriority | None = Query(default=None),
    vehicle_id: int | None = Query(default=None),
    q: str | None = Query(default=None, description="Search by tracking number, customer ref, destination"),
    sort: str = Query(default="id"),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
):
    if sort not in SORTABLE:
        raise HTTPException(status_code=400, detail=f"Invalid sort field. Allowed: {sorted(SORTABLE)}")
    query = db.query(Delivery)
    if status_filter:
        query = query.filter(Delivery.status == status_filter)
    if priority:
        query = query.filter(Delivery.priority == priority)
    if vehicle_id is not None:
        query = query.filter(Delivery.vehicle_id == vehicle_id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Delivery.tracking_number.ilike(like))
            | (Delivery.customer_ref.ilike(like))
            | (Delivery.destination.ilike(like))
        )
    total = query.count()
    col = SORTABLE[sort]
    ordering = col.asc() if order == "asc" else col.desc()
    items = query.order_by(ordering).offset(pg.offset).limit(pg.page_size).all()
    pages = (total + pg.page_size - 1) // pg.page_size if total else 0
    return Page[DeliveryRead](items=items, total=total, page=pg.page, page_size=pg.page_size, pages=pages)


@router.post("", response_model=DeliveryRead, status_code=status.HTTP_201_CREATED)
def create_delivery(payload: DeliveryCreate, db: Session = Depends(get_db)):
    if db.query(Delivery).filter(Delivery.tracking_number == payload.tracking_number).first():
        raise HTTPException(status_code=409, detail=f"Tracking number '{payload.tracking_number}' already exists")
    return delivery_service.create_delivery(db, payload.model_dump())


@router.get("/{delivery_id}", response_model=DeliveryRead)
def get_delivery(delivery_id: int, db: Session = Depends(get_db)):
    d = db.get(Delivery, delivery_id)
    if not d:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return d


@router.patch("/{delivery_id}", response_model=DeliveryRead)
def update_delivery(delivery_id: int, payload: DeliveryUpdate, db: Session = Depends(get_db)):
    return delivery_service.update_delivery(db, delivery_id, payload.model_dump(exclude_unset=True))


@router.post("/{delivery_id}/assign", response_model=DeliveryRead)
def assign_delivery(delivery_id: int, payload: DeliveryAssign, db: Session = Depends(get_db)):
    return delivery_service.assign_delivery(db, delivery_id, payload.vehicle_id)


@router.post("/{delivery_id}/status", response_model=DeliveryRead)
def change_status(delivery_id: int, payload: DeliveryStatusChange, db: Session = Depends(get_db)):
    return delivery_service.change_status(db, delivery_id, payload.status, payload.note)


@router.get("/{delivery_id}/history", response_model=list[DeliveryHistoryRead])
def delivery_history(delivery_id: int, db: Session = Depends(get_db)):
    if not db.get(Delivery, delivery_id):
        raise HTTPException(status_code=404, detail="Delivery not found")
    rows = (
        db.query(DeliveryHistory)
        .filter(DeliveryHistory.delivery_id == delivery_id)
        .order_by(DeliveryHistory.created_at.asc())
        .all()
    )
    return rows
