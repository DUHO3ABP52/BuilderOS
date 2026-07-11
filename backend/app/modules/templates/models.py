from enum import StrEnum
from uuid import UUID

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, EntityMixin


class TemplateCategory(StrEnum):
    CONTRACT = "contract"
    ACT = "act"
    ESTIMATE = "estimate"
    LETTER = "letter"
    OTHER = "other"


class DocumentTemplate(EntityMixin, Base):
    __tablename__ = "document_templates"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("document_templates.id"), nullable=True)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    variables: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
