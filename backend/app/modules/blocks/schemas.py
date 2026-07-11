from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.blocks.models import BlockType


class BlockCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=1, max_length=255)
    block_type: BlockType
    content: str = Field(min_length=1)
    extra: dict[str, Any] | None = None


class BlockRead(BaseModel):
    id: UUID
    slug: str
    title: str
    block_type: BlockType
    content: str
    version: int
    is_archived: bool
    extra: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
