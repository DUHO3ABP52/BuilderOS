from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.modules.calendar.models import CalendarEventType


class CalendarEventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    event_type: CalendarEventType = CalendarEventType.OTHER
    starts_at: datetime
    ends_at: datetime | None = None
    all_day: bool = False
    location: str | None = Field(default=None, max_length=255)
    description: str | None = None
    project_id: UUID | None = None
    task_id: UUID | None = None
    payment_id: UUID | None = None

    @model_validator(mode="after")
    def validate_period(self) -> "CalendarEventCreate":
        if self.ends_at and self.ends_at < self.starts_at:
            raise ValueError("Дата окончания не может быть раньше начала")
        return self


class CalendarEventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    event_type: CalendarEventType | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    all_day: bool | None = None
    location: str | None = Field(default=None, max_length=255)
    description: str | None = None
    project_id: UUID | None = None
    task_id: UUID | None = None
    payment_id: UUID | None = None


class CalendarEventRead(BaseModel):
    id: UUID
    title: str
    event_type: CalendarEventType
    starts_at: datetime
    ends_at: datetime | None
    all_day: bool
    location: str | None
    description: str | None
    project_id: UUID | None
    task_id: UUID | None
    payment_id: UUID | None
    created_by_id: UUID | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
