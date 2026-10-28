from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.vehicle import VehicleStatus, VehicleType


class VehicleBase(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    vehicle_type: VehicleType = VehicleType.VAN
    capacity: int = Field(ge=1, le=500)
    status: VehicleStatus = VehicleStatus.AVAILABLE
    location_zone: str = Field(default="central", min_length=1, max_length=120)
    available: bool = True
    cost_per_km: float = Field(default=1.0, ge=0.0)


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    vehicle_type: Optional[VehicleType] = None
    capacity: Optional[int] = Field(default=None, ge=1, le=500)
    status: Optional[VehicleStatus] = None
    location_zone: Optional[str] = Field(default=None, min_length=1, max_length=120)
    available: Optional[bool] = None
    cost_per_km: Optional[float] = Field(default=None, ge=0.0)


class VehicleRead(VehicleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
