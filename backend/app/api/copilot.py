from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.copilot import CopilotQuery, CopilotResponse
from app.services import copilot_service


router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/query", response_model=CopilotResponse)
def query(payload: CopilotQuery, db: Session = Depends(get_db)):
    return copilot_service.query(db, payload.question).to_dict()
