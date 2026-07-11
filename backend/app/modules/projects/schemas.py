from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.modules.projects.models import ProjectStatus


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str | None = None
    status: ProjectStatus = ProjectStatus.PLANNED
    customer_id: UUID | None = None
    contractor_id: UUID | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    contract_value: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)

    @model_validator(mode="after")
    def validate_period(self) -> "ProjectCreate":
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("Дата окончания не может быть раньше даты начала")
        return self


class ProjectRead(ProjectCreate):
    id: UUID
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = None
    status: ProjectStatus | None = None
    customer_id: UUID | None = None
    contractor_id: UUID | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    contract_value: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)

    @model_validator(mode="after")
    def validate_period(self) -> "ProjectUpdate":
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("Дата окончания не может быть раньше даты начала")
        return self
