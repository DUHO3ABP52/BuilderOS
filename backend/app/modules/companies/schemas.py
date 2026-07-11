from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.companies.models import CompanyKind


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    kind: CompanyKind
    inn: str | None = Field(default=None, pattern=r"^\d{10}(\d{2})?$")
    kpp: str | None = Field(default=None, pattern=r"^\d{9}$")
    ogrn: str | None = Field(default=None, pattern=r"^\d{13}(\d{2})?$")
    legal_address: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = Field(default=None, max_length=320)


class CompanyRead(CompanyCreate):
    id: UUID
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    kind: CompanyKind | None = None
    inn: str | None = Field(default=None, pattern=r"^\d{10}(\d{2})?$")
    kpp: str | None = Field(default=None, pattern=r"^\d{9}$")
    ogrn: str | None = Field(default=None, pattern=r"^\d{13}(\d{2})?$")
    legal_address: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = Field(default=None, max_length=320)
