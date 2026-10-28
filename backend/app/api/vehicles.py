from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import Pagination, pagination_params
from app.models.vehicle import Vehicle, VehicleStatus
from app.schemas.common import Page
from app.schemas.vehicle import VehicleCreate, VehicleRead, VehicleUpdate


router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=Page[VehicleRead])
def list_vehicles(
    db: Session = Depends(get_db),
    pg: Pagination = Depends(pagination_params),
    status_filter: VehicleStatus | None = Query(default=None, alias="status"),
    available: bool | None = Query(default=None),
    q: str | None = Query(default=None, description="Search by code or zone"),
):
    query = db.query(Vehicle)
    if status_filter:
        query = query.filter(Vehicle.status == status_filter)
    if available is not None:
        query = query.filter(Vehicle.available == available)
    if q:
        like = f"%{q}%"
        query = query.filter((Vehicle.code.ilike(like)) | (Vehicle.location_zone.ilike(like)))
    total = query.count()
    items = query.order_by(Vehicle.id.asc()).offset(pg.offset).limit(pg.page_size).all()
    pages = (total + pg.page_size - 1) // pg.page_size if total else 0
    return Page[VehicleRead](items=items, total=total, page=pg.page, page_size=pg.page_size, pages=pages)


@router.post("", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
def create_vehicle(payload: VehicleCreate, db: Session = Depends(get_db)):
    if db.query(Vehicle).filter(Vehicle.code == payload.code).first():
        raise HTTPException(status_code=409, detail=f"Vehicle code '{payload.code}' already exists")
    v = Vehicle(**payload.model_dump())
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@router.get("/{vehicle_id}", response_model=VehicleRead)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    v = db.get(Vehicle, vehicle_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return v


@router.patch("/{vehicle_id}", response_model=VehicleRead)
def update_vehicle(vehicle_id: int, payload: VehicleUpdate, db: Session = Depends(get_db)):
    v = db.get(Vehicle, vehicle_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    for k, val in payload.model_dump(exclude_unset=True).items():
        setattr(v, k, val)
    # Keep availability in sync with status
    if payload.status is not None and payload.available is None:
        v.available = payload.status == VehicleStatus.AVAILABLE
    db.commit()
    db.refresh(v)
    return v
