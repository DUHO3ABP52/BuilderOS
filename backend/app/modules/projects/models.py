from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, EntityMixin


class ProjectStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class Project(EntityMixin, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default=ProjectStatus.PLANNED, nullable=False)
    customer_id: Mapped[UUID | None] = mapped_column(ForeignKey("companies.id"))
    contractor_id: Mapped[UUID | None] = mapped_column(ForeignKey("companies.id"))
    starts_on: Mapped[date | None] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    contract_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
