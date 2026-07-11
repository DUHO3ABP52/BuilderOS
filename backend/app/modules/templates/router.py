from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.documents.engine.parser import parse_docx
from app.modules.documents.engine.sample_import import import_sample_to_builder_document
from app.modules.events.models import AuditAction
from app.modules.events.service import log_event
from app.modules.memory.learning import learn_from_template_version
from app.modules.templates.importer import import_sample_as_template
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


@router.post("/import/sample", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
async def import_sample_template(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    slug: str | None = Form(default=None),
    category: str | None = Form(default=None),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DocumentTemplate:
    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(status_code=422, detail="Пустой файл")
    try:
        template, result = import_sample_as_template(
            session,
            data=content_bytes,
            filename=file.filename,
            content_type=file.content_type,
            user_id=user.id,
            name=name,
            slug=slug,
            category=category,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=422, detail=f"Не удалось разобрать образец: {error}") from error

    log_event(
        session,
        actor_id=user.id,
        entity_type="template",
        entity_id=template.id,
        action=AuditAction.CREATE,
        summary=f"Импортирован шаблон из образца: {template.name}",
        payload={
            "filename": file.filename,
            "source_format": result.source_format,
            "variables": [item.key for item in result.variables],
            "warnings": result.warnings,
        },
    )
    session.commit()
    session.refresh(template)
    return template


@router.post("/import/preview")
async def preview_sample_template(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
) -> dict:
    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(status_code=422, detail="Пустой файл")
    try:
        result = import_sample_to_builder_document(
            content_bytes,
            filename=file.filename,
            content_type=file.content_type,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=422, detail=f"Не удалось разобрать образец: {error}") from error
    return {
        "source_format": result.source_format,
        "title": result.document.title,
        "doc_type": result.document.doc_type,
        "sections": [section.model_dump() for section in result.document.sections],
        "variables": [item.model_dump() for item in result.variables],
        "sample_values": result.sample_values,
        "warnings": result.warnings,
        "excerpt": result.extracted_text[:1200],
    }


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
    notes = learn_from_template_version(session, parent=parent, new_template=template, user_id=user.id)
    log_event(
        session,
        actor_id=user.id,
        entity_type="template",
        entity_id=template.id,
        action=AuditAction.VERSION,
        summary=f"Создана версия шаблона {template.name} v{template.version}",
        payload={"learned": notes},
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
