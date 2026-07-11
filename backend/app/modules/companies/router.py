from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.companies.models import Company
from app.modules.companies.schemas import CompanyCreate, CompanyRead, CompanyUpdate
from app.modules.events.models import AuditAction
from app.modules.events.service import log_event

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CompanyCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Company:
    company = Company(**payload.model_dump())
    session.add(company)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Компания с таким ИНН уже существует") from error
    log_event(
        session,
        actor_id=user.id,
        entity_type="company",
        entity_id=company.id,
        action=AuditAction.CREATE,
        summary=f"Создана компания {company.name}",
    )
    session.commit()
    session.refresh(company)
    return company


@router.get("", response_model=list[CompanyRead])
def list_companies(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[Company]:
    return list(session.scalars(select(Company).where(Company.is_archived.is_(False)).order_by(Company.name)))


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(
    company_id: UUID,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> Company:
    company = session.get(Company, company_id)
    if company is None or company.is_archived:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    return company


@router.patch("/{company_id}", response_model=CompanyRead)
def update_company(
    company_id: UUID,
    payload: CompanyUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Company:
    company = session.get(Company, company_id)
    if company is None or company.is_archived:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Компания с таким ИНН уже существует") from error
    log_event(
        session,
        actor_id=user.id,
        entity_type="company",
        entity_id=company.id,
        action=AuditAction.UPDATE,
        summary=f"Обновлена компания {company.name}",
    )
    session.commit()
    session.refresh(company)
    return company


@router.post("/{company_id}/archive", response_model=CompanyRead)
def archive_company(
    company_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Company:
    company = session.get(Company, company_id)
    if company is None or company.is_archived:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    company.is_archived = True
    log_event(
        session,
        actor_id=user.id,
        entity_type="company",
        entity_id=company.id,
        action=AuditAction.ARCHIVE,
        summary=f"Архивирована компания {company.name}",
    )
    session.commit()
    session.refresh(company)
    return company
