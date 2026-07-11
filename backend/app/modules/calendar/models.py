from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, EntityMixin


class CalendarEventType(StrEnum):
    MEETING = "meeting"
    DEADLINE = "deadline"
    SITE_VISIT = "site_visit"
    PAYMENT = "payment"
    DOCUMENT = "document"
    OTHER = "other"


class CalendarEvent(EntityMixin, Base):
    __tablename__ = "calendar_events"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), default=CalendarEventType.OTHER, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    all_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=True)
    task_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("tasks.id"), nullable=True)
    payment_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("payments.id"), nullable=True)
    created_by_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
