import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_user
from app.models.user import User
from app.models.simulation import Simulation
from app.schemas.simulation import SimulationCreate, SimulationRead
from app.services import simulator


router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.post("", response_model=SimulationRead)
def create_simulation(payload: SimulationCreate, db: Session = Depends(get_db), _user: User = Depends(require_user)):
    try:
        result = simulator.run_simulation(db, payload.scenario.value, payload.params)
    except ValueError as e:
        raise HTTPException(400, str(e))
    sim = Simulation(
        scenario=payload.scenario,
        params_json=json.dumps(payload.params),
        baseline_metrics_json=json.dumps(result["baseline_metrics"]),
        simulated_metrics_json=json.dumps(result["simulated_metrics"]),
        diff_json=json.dumps(result["diff"]),
        explanation=result["explanation"],
    )
    db.add(sim)
    db.commit()
    db.refresh(sim)
    return sim


@router.get("/{sim_id}", response_model=SimulationRead)
def get_simulation(sim_id: int, db: Session = Depends(get_db)):
    s = db.get(Simulation, sim_id)
    if not s:
        raise HTTPException(404, "Simulation not found")
    return s
