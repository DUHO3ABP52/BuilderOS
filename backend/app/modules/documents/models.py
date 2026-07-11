from enum import StrEnum
from uuid import UUID

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, EntityMixin


class DocumentStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class Document(EntityMixin, Base):
    __tablename__ = "documents"

    project_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=True)
    template_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("document_templates.id"), nullable=True)
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=DocumentStatus.DRAFT, nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(EntityMixin, Base):
    __tablename__ = "document_versions"

    document_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("documents.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    variables: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    document: Mapped[Document] = relationship(back_populates="versions")
