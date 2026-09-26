from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.booking import BookingStatus


class BookingCreate(BaseModel):
    test_id: int = Field(gt=0)
    centre_id: int = Field(gt=0)
    appointment_at: datetime


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    test_id: int
    centre_id: int
    appointment_at: datetime
    amount: Decimal
    status: BookingStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None
