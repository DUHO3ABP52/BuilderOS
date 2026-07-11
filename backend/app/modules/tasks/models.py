from datetime import date
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, EntityMixin


class TaskStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class Task(EntityMixin, Base):
    __tablename__ = "tasks"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=TaskStatus.OPEN, nullable=False)
    project_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=True)
    document_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("documents.id"), nullable=True)
    due_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
