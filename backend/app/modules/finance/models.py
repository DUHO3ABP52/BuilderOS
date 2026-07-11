from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, EntityMixin


class PaymentDirection(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"


class PaymentKind(StrEnum):
    ADVANCE = "advance"
    ACT = "act"
    INVOICE = "invoice"
    SALARY = "salary"
    MATERIAL = "material"
    OTHER = "other"


class PaymentStatus(StrEnum):
    PLANNED = "planned"
    DUE = "due"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Payment(EntityMixin, Base):
    __tablename__ = "payments"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), default=PaymentKind.OTHER, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=PaymentStatus.PLANNED, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="RUB", nullable=False)
    project_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=True)
    company_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=True)
    document_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("documents.id"), nullable=True)
    due_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    paid_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
