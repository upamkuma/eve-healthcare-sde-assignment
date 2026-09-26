from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.payment import PaymentStatus


class PaymentCreate(BaseModel):
    booking_id: int = Field(gt=0)
    simulate: Literal["SUCCESS", "FAILED"] = "SUCCESS"
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=120)


class PaymentWebhook(BaseModel):
    event_id: str = Field(min_length=1, max_length=120)
    provider_payment_id: str | None = Field(default=None, min_length=1, max_length=100)
    booking_id: int | None = Field(default=None, gt=0)
    status: Literal["SUCCESS", "FAILED"]


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    provider_payment_id: str
    provider_event_id: str | None = None
    idempotency_key: str | None = None
    amount: Decimal
    status: PaymentStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None
