from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.memory.models import MemoryKind


class MemoryCreate(BaseModel):
    kind: MemoryKind = MemoryKind.FACT
    key: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1)
    confidence: float = Field(default=1.0, ge=0, le=1)
    source: str | None = None
    project_id: UUID | None = None


class MemoryRead(BaseModel):
    id: UUID
    kind: MemoryKind
    key: str
    content: str
    confidence: float
    source: str | None
    project_id: UUID | None
    created_by_id: UUID | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
