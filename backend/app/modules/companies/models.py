from enum import StrEnum

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, EntityMixin


class CompanyKind(StrEnum):
    CUSTOMER = "customer"
    CONTRACTOR = "contractor"
    SUPPLIER = "supplier"


class Company(EntityMixin, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    inn: Mapped[str | None] = mapped_column(String(12), unique=True)
    kpp: Mapped[str | None] = mapped_column(String(9))
    ogrn: Mapped[str | None] = mapped_column(String(15))
    legal_address: Mapped[str | None] = mapped_column(Text)
    contact_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(320))
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
