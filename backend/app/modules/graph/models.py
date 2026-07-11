from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, EntityMixin


class GraphRelationType(StrEnum):
    HAS_CUSTOMER = "has_customer"
    HAS_CONTRACTOR = "has_contractor"
    HAS_DOCUMENT = "has_document"
    HAS_TASK = "has_task"
    HAS_PAYMENT = "has_payment"
    HAS_EVENT = "has_event"
    HAS_MEMORY = "has_memory"
    RELATED_TO = "related_to"
    MENTIONS = "mentions"
    DEPENDS_ON = "depends_on"


class GraphEntityType(StrEnum):
    PROJECT = "project"
    COMPANY = "company"
    DOCUMENT = "document"
    TASK = "task"
    PAYMENT = "payment"
    EVENT = "event"
    MEMORY = "memory"
    NOTE = "note"


class GraphEdge(EntityMixin, Base):
    """Ручные / AI-связи поверх вычисляемого графа объекта."""

    __tablename__ = "graph_edges"

    project_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=False)
    from_type: Mapped[str] = mapped_column(String(32), nullable=False)
    from_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    to_type: Mapped[str] = mapped_column(String(32), nullable=False)
    to_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    relation: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    created_by_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
