from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.companies.models import Company
from app.modules.companies.schemas import CompanyCreate, CompanyRead

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def create_company(payload: CompanyCreate, session: Session = Depends(get_session)) -> Company:
    company = Company(**payload.model_dump())
    session.add(company)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Компания с таким ИНН уже существует") from error
    session.refresh(company)
    return company


@router.get("", response_model=list[CompanyRead])
def list_companies(session: Session = Depends(get_session)) -> list[Company]:
    return list(session.scalars(select(Company).where(Company.is_archived.is_(False)).order_by(Company.name)))
