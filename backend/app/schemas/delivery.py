from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.delivery import DeliveryPriority, DeliveryStatus


class DeliveryBase(BaseModel):
    tracking_number: str = Field(min_length=3, max_length=40)
    customer_ref: str = Field(min_length=1, max_length=120)
    origin: str = Field(min_length=1, max_length=200)
    destination: str = Field(min_length=1, max_length=200)
    scheduled_dispatch: datetime
    promised_deadline: datetime
    priority: DeliveryPriority = DeliveryPriority.NORMAL
    distance_km: float = Field(default=0.0, ge=0.0)
    cost_estimate: float = Field(default=0.0, ge=0.0)
    weather_exposure: float = Field(default=0.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _deadline_after_dispatch(self) -> "DeliveryBase":
        if self.promised_deadline <= self.scheduled_dispatch:
            raise ValueError("promised_deadline must be after scheduled_dispatch")
        return self


class DeliveryCreate(DeliveryBase):
    vehicle_id: Optional[int] = None


class DeliveryUpdate(BaseModel):
    customer_ref: Optional[str] = Field(default=None, min_length=1, max_length=120)
    origin: Optional[str] = Field(default=None, min_length=1, max_length=200)
    destination: Optional[str] = Field(default=None, min_length=1, max_length=200)
    scheduled_dispatch: Optional[datetime] = None
    promised_deadline: Optional[datetime] = None
    priority: Optional[DeliveryPriority] = None
    distance_km: Optional[float] = Field(default=None, ge=0.0)
    cost_estimate: Optional[float] = Field(default=None, ge=0.0)
    weather_exposure: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    estimated_arrival: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None


class DeliveryAssign(BaseModel):
    vehicle_id: Optional[int]  # None to unassign


class DeliveryStatusChange(BaseModel):
    status: DeliveryStatus
    note: Optional[str] = Field(default=None, max_length=500)


class DeliveryRead(BaseModel):
    id: int
    tracking_number: str
    customer_ref: str
    origin: str
    destination: str
    scheduled_dispatch: datetime
    promised_deadline: datetime
    estimated_arrival: Optional[datetime]
    actual_arrival: Optional[datetime]
    priority: DeliveryPriority
    status: DeliveryStatus
    vehicle_id: Optional[int]
    distance_km: float
    cost_estimate: float
    weather_exposure: float
    risk_score: float
    risk_explanation: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeliveryHistoryRead(BaseModel):
    id: int
    delivery_id: int
    event_type: str
    from_status: Optional[str]
    to_status: Optional[str]
    from_vehicle_id: Optional[int]
    to_vehicle_id: Optional[int]
    note: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
