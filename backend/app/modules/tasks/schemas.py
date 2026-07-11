from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.tasks.models import TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    project_id: UUID | None = None
    document_id: UUID | None = None
    due_on: date | None = None
    status: TaskStatus = TaskStatus.OPEN


class TaskRead(BaseModel):
    id: UUID
    title: str
    description: str | None
    status: TaskStatus
    project_id: UUID | None
    document_id: UUID | None
    due_on: date | None
    created_by_id: UUID | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: TaskStatus | None = None
    project_id: UUID | None = None
    document_id: UUID | None = None
    due_on: date | None = None
