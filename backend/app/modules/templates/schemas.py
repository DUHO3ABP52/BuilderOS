from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.documents.engine.builder_document import BuilderDocument, VariableDefinition
from app.modules.templates.models import TemplateCategory


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9-]+$")
    category: TemplateCategory
    content: BuilderDocument
    variables: list[VariableDefinition] = Field(default_factory=list)
    description: str | None = None


class TemplateRead(BaseModel):
    id: UUID
    name: str
    slug: str
    category: TemplateCategory
    version: int
    parent_id: UUID | None
    content: dict[str, Any]
    variables: list[dict[str, Any]]
    description: str | None
    is_archived: bool
    created_by_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
