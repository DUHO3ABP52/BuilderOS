from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.finance.models import PaymentDirection, PaymentKind, PaymentStatus


class PaymentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    direction: PaymentDirection
    kind: PaymentKind = PaymentKind.OTHER
    status: PaymentStatus = PaymentStatus.PLANNED
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="RUB", min_length=3, max_length=8)
    project_id: UUID | None = None
    company_id: UUID | None = None
    document_id: UUID | None = None
    due_on: date | None = None
    paid_on: date | None = None
    description: str | None = None


class PaymentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    direction: PaymentDirection | None = None
    kind: PaymentKind | None = None
    status: PaymentStatus | None = None
    amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    project_id: UUID | None = None
    company_id: UUID | None = None
    document_id: UUID | None = None
    due_on: date | None = None
    paid_on: date | None = None
    description: str | None = None


class PaymentRead(BaseModel):
    id: UUID
    title: str
    direction: PaymentDirection
    kind: PaymentKind
    status: PaymentStatus
    amount: Decimal
    currency: str
    project_id: UUID | None
    company_id: UUID | None
    document_id: UUID | None
    due_on: date | None
    paid_on: date | None
    description: str | None
    created_by_id: UUID | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
