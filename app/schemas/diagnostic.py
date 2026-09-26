from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CentreCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    location: str = Field(min_length=2, max_length=255)


class CentreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    location: str | None = Field(default=None, min_length=2, max_length=255)


class TestCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class TestUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)


class TestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    centre_id: int
    name: str
    description: str | None
    price: Decimal
    created_at: datetime | None = None


class CentreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str
    created_at: datetime | None = None
    tests: list[TestResponse] = []
