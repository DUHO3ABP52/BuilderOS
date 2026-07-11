from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.knowledge.models import KnowledgeCategory


class KnowledgeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    category: KnowledgeCategory
    source_type: str = "text"
    content: str = Field(min_length=1)
    source_metadata: dict[str, Any] | None = None


class KnowledgeRead(BaseModel):
    id: UUID
    title: str
    category: KnowledgeCategory
    source_type: str
    content: str
    source_metadata: dict[str, Any] | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
