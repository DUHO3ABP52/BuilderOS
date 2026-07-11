from enum import StrEnum

from sqlalchemy import Boolean, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, EntityMixin


class KnowledgeCategory(StrEnum):
    SP = "sp"
    SNIP = "snip"
    GOST = "gost"
    INTERNAL = "internal"
    TEMPLATE = "template"
    OTHER = "other"


class KnowledgeItem(EntityMixin, Base):
    __tablename__ = "knowledge_items"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), default="text", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
