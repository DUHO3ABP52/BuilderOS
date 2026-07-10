from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.companies.models import Company
from app.modules.projects.models import Project
from app.modules.projects.schemas import ProjectCreate, ProjectRead

router = APIRouter(prefix="/projects", tags=["projects"])


def ensure_company_exists(session: Session, company_id: UUID | None, field: str) -> None:
    if company_id is None:
        return
    company = session.get(Company, company_id)
    if company is None or company.is_archived:
        raise HTTPException(status_code=422, detail=f"{field}: компания не найдена")


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, session: Session = Depends(get_session)) -> Project:
    ensure_company_exists(session, payload.customer_id, "customer_id")
    ensure_company_exists(session, payload.contractor_id, "contractor_id")
    project = Project(**payload.model_dump())
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(session: Session = Depends(get_session)) -> list[Project]:
    return list(session.scalars(select(Project).where(Project.is_archived.is_(False)).order_by(Project.created_at.desc())))
