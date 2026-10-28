import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.delivery import Delivery
from app.models.risk_assessment import RiskAssessment
from app.models.vehicle import Vehicle
from app.schemas.risk import RiskResultRead
from app.services import risk_engine


router = APIRouter(prefix="/risk", tags=["risk"])


class AssessRequest(BaseModel):
    delivery_id: int


@router.post("/assess", response_model=RiskResultRead)
def assess(payload: AssessRequest, db: Session = Depends(get_db)):
    d = db.get(Delivery, payload.delivery_id)
    if not d:
        raise HTTPException(404, "Delivery not found")
    v = db.get(Vehicle, d.vehicle_id) if d.vehicle_id else None
    result = risk_engine.assess(d, v)

    # persist latest assessment + update cached fields
    d.risk_score = result.score
    d.risk_explanation = (
        f"rule-based; category={result.category}; "
        f"confidence={result.confidence:.2f}; intervention={result.intervention}"
    )
    db.add(RiskAssessment(
        delivery_id=d.id,
        score=result.score,
        category=result.category,
        confidence=result.confidence,
        intervention=result.intervention,
        factors_json=json.dumps(result.factors),
        assessed_at=datetime.now(timezone.utc),
    ))
    db.commit()

    return RiskResultRead(
        delivery_id=result.delivery_id,
        score=result.score,
        category=result.category,
        confidence=result.confidence,
        intervention=result.intervention,
        factors=result.factors,
        assessed_at=result.assessed_at,
    )
