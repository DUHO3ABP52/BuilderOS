from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.companies.models import Company
from app.modules.events.models import AuditAction
from app.modules.events.service import log_event
from app.modules.projects.models import Project
from app.modules.projects.schemas import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


def _ensure_company_exists(session: Session, company_id: UUID | None, field: str) -> None:
    if company_id is None:
        return
    company = session.get(Company, company_id)
    if company is None or company.is_archived:
        raise HTTPException(status_code=422, detail=f"{field}: компания не найдена")


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Project:
    _ensure_company_exists(session, payload.customer_id, "customer_id")
    _ensure_company_exists(session, payload.contractor_id, "contractor_id")
    project = Project(**payload.model_dump())
    session.add(project)
    session.flush()
    log_event(
        session,
        actor_id=user.id,
        entity_type="project",
        entity_id=project.id,
        action=AuditAction.CREATE,
        summary=f"Создан объект {project.name}",
    )
    session.commit()
    session.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[Project]:
    return list(session.scalars(select(Project).where(Project.is_archived.is_(False)).order_by(Project.created_at.desc())))


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: UUID,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> Project:
    project = session.get(Project, project_id)
    if project is None or project.is_archived:
        raise HTTPException(status_code=404, detail="Объект не найден")
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Project:
    project = session.get(Project, project_id)
    if project is None or project.is_archived:
        raise HTTPException(status_code=404, detail="Объект не найден")
    data = payload.model_dump(exclude_unset=True)
    _ensure_company_exists(session, data.get("customer_id"), "customer_id")
    _ensure_company_exists(session, data.get("contractor_id"), "contractor_id")
    for field, value in data.items():
        setattr(project, field, value)
    log_event(
        session,
        actor_id=user.id,
        entity_type="project",
        entity_id=project.id,
        action=AuditAction.UPDATE,
        summary=f"Обновлен объект {project.name}",
    )
    session.commit()
    session.refresh(project)
    return project


@router.post("/{project_id}/archive", response_model=ProjectRead)
def archive_project(
    project_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Project:
    project = session.get(Project, project_id)
    if project is None or project.is_archived:
        raise HTTPException(status_code=404, detail="Объект не найден")
    project.is_archived = True
    log_event(
        session,
        actor_id=user.id,
        entity_type="project",
        entity_id=project.id,
        action=AuditAction.ARCHIVE,
        summary=f"Архивирован объект {project.name}",
    )
    session.commit()
    session.refresh(project)
    return project
