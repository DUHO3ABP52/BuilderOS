from enum import StrEnum
from uuid import UUID

from sqlalchemy import JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, EntityMixin


class AuditAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    ARCHIVE = "archive"
    RESTORE = "restore"
    EXPORT = "export"
    VERSION = "version"


class AuditEvent(EntityMixin, Base):
    __tablename__ = "audit_events"

    actor_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(String(512), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
