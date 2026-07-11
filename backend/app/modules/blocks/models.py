from enum import StrEnum

from sqlalchemy import Boolean, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, EntityMixin


class BlockType(StrEnum):
    HEADER = "header"
    SUBJECT = "subject"
    PRICE = "price"
    RESPONSIBILITY = "responsibility"
    PAYMENT = "payment"
    FORCE_MAJEURE = "force_majeure"
    GUARANTEE = "guarantee"
    DISPUTES = "disputes"
    APPENDIX = "appendix"
    SIGNATURES = "signatures"
    GENERIC = "generic"


class DocumentBlock(EntityMixin, Base):
    __tablename__ = "document_blocks"

    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    block_type: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
