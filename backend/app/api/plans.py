from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import Pagination, pagination_params
from app.models.recovery_plan import PlanKind, PlanStatus, RecoveryPlan
from app.schemas.action import ActionRead, DecisionRequest, ExecuteRequest, SubmitRequest
from app.schemas.common import Page
from app.schemas.plan import PlanRead
from app.core.config import settings
from app.services import approval_service, plan_service


router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("/generate", response_model=list[PlanRead])
def generate_plans(db: Session = Depends(get_db)):
    return plan_service.generate_and_persist(db)


@router.get("", response_model=Page[PlanRead])
def list_plans(
    db: Session = Depends(get_db),
    pg: Pagination = Depends(pagination_params),
    kind: PlanKind | None = Query(default=None),
    status_filter: PlanStatus | None = Query(default=None, alias="status"),
):
    q = db.query(RecoveryPlan)
    if kind:
        q = q.filter(RecoveryPlan.kind == kind)
    if status_filter:
        q = q.filter(RecoveryPlan.status == status_filter)
    total = q.count()
    items = q.order_by(RecoveryPlan.id.desc()).offset(pg.offset).limit(pg.page_size).all()
    pages = (total + pg.page_size - 1) // pg.page_size if total else 0
    return Page[PlanRead](items=items, total=total, page=pg.page, page_size=pg.page_size, pages=pages)


@router.get("/{plan_id}", response_model=PlanRead)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    p = db.get(RecoveryPlan, plan_id)
    if not p:
        raise HTTPException(404, "Plan not found")
    return p


@router.post("/{plan_id}/submit", response_model=ActionRead)
def submit_plan(plan_id: int, payload: SubmitRequest, db: Session = Depends(get_db)):
    return approval_service.submit_plan(db, plan_id, actor=payload.actor or settings.ADMIN_DISPLAY_NAME)
