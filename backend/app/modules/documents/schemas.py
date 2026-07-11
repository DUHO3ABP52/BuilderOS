from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.documents.engine.builder_document import BuilderDocument
from app.modules.documents.models import DocumentStatus


class DocumentCreate(BaseModel):
    project_id: UUID | None = None
    template_id: UUID | None = None
    doc_type: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    content: BuilderDocument
    variables: dict[str, Any] = Field(default_factory=dict)
    change_summary: str | None = None


class DocumentFromTemplate(BaseModel):
    project_id: UUID | None = None
    title: str | None = None
    variables: dict[str, Any] = Field(default_factory=dict)


class DocumentVersionRead(BaseModel):
    id: UUID
    version_number: int
    content: dict[str, Any]
    variables: dict[str, Any]
    change_summary: str | None
    created_by_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentRead(BaseModel):
    id: UUID
    project_id: UUID | None
    template_id: UUID | None
    doc_type: str
    title: str
    status: DocumentStatus
    current_version: int
    is_archived: bool
    created_by_id: UUID | None
    created_at: datetime
    updated_at: datetime
    versions: list[DocumentVersionRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}
