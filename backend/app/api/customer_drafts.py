from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import message_service


router = APIRouter(prefix="/customer-drafts", tags=["customer-drafts"])


@router.get("/{delivery_id}")
def get_draft(delivery_id: int, db: Session = Depends(get_db)):
    draft = message_service.create_draft(db, delivery_id)
    if draft is None:
        raise HTTPException(404, "Delivery not found")
    return draft.to_dict()
