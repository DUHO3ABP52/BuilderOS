from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.documents.engine.parser import parse_docx
from app.modules.events.models import AuditAction
from app.modules.events.service import log_event
from app.modules.templates.models import DocumentTemplate
from app.modules.templates.schemas import TemplateCreate, TemplateRead
from app.modules.templates.service import create_template, create_template_version, list_templates

router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
def create_template_endpoint(
    payload: TemplateCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DocumentTemplate:
    template = create_template(session, payload, user.id)
    log_event(
        session,
        actor_id=user.id,
        entity_type="template",
        entity_id=template.id,
        action=AuditAction.CREATE,
        summary=f"Создан шаблон {template.name}",
    )
    session.commit()
    session.refresh(template)
    return template


@router.get("", response_model=list[TemplateRead])
def list_templates_endpoint(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[DocumentTemplate]:
    return list_templates(session)


@router.get("/{template_id}", response_model=TemplateRead)
def get_template(
    template_id: UUID,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> DocumentTemplate:
    template = session.get(DocumentTemplate, template_id)
    if template is None or template.is_archived:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    return template


@router.post("/{template_id}/versions", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
def create_version(
    template_id: UUID,
    payload: TemplateCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DocumentTemplate:
    parent = session.get(DocumentTemplate, template_id)
    if parent is None or parent.is_archived:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    template = create_template_version(session, parent, payload, user.id)
    log_event(
        session,
        actor_id=user.id,
        entity_type="template",
        entity_id=template.id,
        action=AuditAction.VERSION,
        summary=f"Создана версия шаблона {template.name} v{template.version}",
    )
    session.commit()
    session.refresh(template)
    return template


@router.post("/import/docx", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
async def import_docx_template(
    name: str,
    slug: str,
    category: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DocumentTemplate:
    content_bytes = await file.read()
    builder_document = parse_docx(content_bytes)
    payload = TemplateCreate(
        name=name,
        slug=slug,
        category=category,
        content=builder_document.model_copy(update={"title": name}),
        description=f"Импортирован из {file.filename}",
    )
    template = create_template(session, payload, user.id)
    log_event(
        session,
        actor_id=user.id,
        entity_type="template",
        entity_id=template.id,
        action=AuditAction.CREATE,
        summary=f"Импортирован шаблон из DOCX: {template.name}",
        payload={"filename": file.filename},
    )
    session.commit()
    session.refresh(template)
    return template


@router.post("/{template_id}/archive", response_model=TemplateRead)
def archive_template(
    template_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DocumentTemplate:
    template = session.get(DocumentTemplate, template_id)
    if template is None or template.is_archived:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    template.is_archived = True
    log_event(
        session,
        actor_id=user.id,
        entity_type="template",
        entity_id=template.id,
        action=AuditAction.ARCHIVE,
        summary=f"Архивирован шаблон {template.name}",
    )
    session.commit()
    session.refresh(template)
    return template
