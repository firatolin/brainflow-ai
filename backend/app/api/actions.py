from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import Pagination, pagination_params
from app.models.operational_action import ActionStatus, OperationalAction
from app.schemas.action import ActionRead, DecisionRequest, ExecuteRequest, SubmitRequest
from app.schemas.common import Page
from app.services import approval_service


router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("", response_model=Page[ActionRead])
def list_actions(
    db: Session = Depends(get_db),
    pg: Pagination = Depends(pagination_params),
    status_filter: ActionStatus | None = Query(default=None, alias="status"),
):
    q = db.query(OperationalAction)
    if status_filter:
        q = q.filter(OperationalAction.status == status_filter)
    total = q.count()
    items = q.order_by(OperationalAction.id.desc()).offset(pg.offset).limit(pg.page_size).all()
    pages = (total + pg.page_size - 1) // pg.page_size if total else 0
    return Page[ActionRead](items=items, total=total, page=pg.page, page_size=pg.page_size, pages=pages)


@router.get("/{action_id}", response_model=ActionRead)
def get_action(action_id: int, db: Session = Depends(get_db)):
    a = db.get(OperationalAction, action_id)
    if not a:
        from fastapi import HTTPException
        raise HTTPException(404, "Action not found")
    return a


@router.post("/{action_id}/approve", response_model=ActionRead)
def approve(action_id: int, payload: DecisionRequest, db: Session = Depends(get_db)):
    return approval_service.approve_action(db, action_id, reviewer=payload.reviewer, note=payload.note)


@router.post("/{action_id}/reject", response_model=ActionRead)
def reject(action_id: int, payload: DecisionRequest, db: Session = Depends(get_db)):
    return approval_service.reject_action(db, action_id, reviewer=payload.reviewer, note=payload.note)


@router.post("/{action_id}/execute", response_model=ActionRead)
def execute(action_id: int, payload: ExecuteRequest, db: Session = Depends(get_db)):
    return approval_service.execute_action(db, action_id, reviewer=payload.reviewer)
