from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import Pagination, pagination_params
from app.models.scan_run import ScanRun
from app.schemas.common import Page
from app.schemas.scan import ScanRunRead
from app.services import scan_service


router = APIRouter(prefix="/scan-runs", tags=["scan-runs"])


@router.get("", response_model=Page[ScanRunRead])
def list_scan_runs(
    db: Session = Depends(get_db),
    pg: Pagination = Depends(pagination_params),
):
    q = db.query(ScanRun).order_by(ScanRun.started_at.desc())
    total = q.count()
    items = q.offset(pg.offset).limit(pg.page_size).all()
    pages = (total + pg.page_size - 1) // pg.page_size if total else 0
    return Page[ScanRunRead](items=items, total=total, page=pg.page, page_size=pg.page_size, pages=pages)


@router.post("", response_model=ScanRunRead)
def trigger_scan_run(db: Session = Depends(get_db)):
    return scan_service.run_scan(db, triggered_by="manual")
