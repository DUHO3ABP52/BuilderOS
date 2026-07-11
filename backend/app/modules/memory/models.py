from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, EntityMixin


class MemoryKind(StrEnum):
    PREFERENCE = "preference"
    FACT = "fact"
    PATTERN = "pattern"
    TEMPLATE_HINT = "template_hint"


class MemoryFact(EntityMixin, Base):
    __tablename__ = "memory_facts"

    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    project_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=True)
    created_by_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
