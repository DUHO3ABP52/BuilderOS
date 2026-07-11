from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.documents.engine.builder_document import BuilderDocument
from app.modules.documents.engine.renderer import export_docx, export_html, export_pdf
from app.modules.documents.models import Document
from app.modules.documents.schemas import DocumentCreate, DocumentFromTemplate, DocumentRead, DocumentVersionRead
from app.modules.documents.service import create_document, create_document_version, get_document, list_documents
from app.modules.events.models import AuditAction
from app.modules.events.service import log_event
from app.modules.templates.models import DocumentTemplate

router = APIRouter(prefix="/documents", tags=["documents"])


def _attachment_headers(filename: str, extension: str) -> dict[str, str]:
    safe_name = "".join(char if char.isascii() and char not in '\\/"' else "_" for char in filename).strip("._") or "document"
    encoded = quote(f"{filename}.{extension}")
    return {"Content-Disposition": f"attachment; filename=\"{safe_name}.{extension}\"; filename*=UTF-8''{encoded}"}



def _to_read(document: Document) -> DocumentRead:
    return DocumentRead(
        id=document.id,
        project_id=document.project_id,
        template_id=document.template_id,
        doc_type=document.doc_type,
        title=document.title,
        status=document.status,
        current_version=document.current_version,
        is_archived=document.is_archived,
        created_by_id=document.created_by_id,
        created_at=document.created_at,
        updated_at=document.updated_at,
        versions=[DocumentVersionRead.model_validate(version) for version in document.versions],
    )


def _latest_builder_document(document: Document) -> BuilderDocument:
    latest = max(document.versions, key=lambda item: item.version_number)
    return BuilderDocument.model_validate({**latest.content, "variables": latest.variables})


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document_endpoint(
    payload: DocumentCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DocumentRead:
    try:
        document = create_document(session, payload, user.id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    log_event(
        session,
        actor_id=user.id,
        entity_type="document",
        entity_id=document.id,
        action=AuditAction.CREATE,
        summary=f"Создан документ {document.title}",
    )
    session.commit()
    refreshed = get_document(session, document.id)
    assert refreshed is not None
    return _to_read(refreshed)


@router.get("", response_model=list[DocumentRead])
def list_documents_endpoint(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[DocumentRead]:
    return [_to_read(document) for document in list_documents(session)]


@router.get("/{document_id}", response_model=DocumentRead)
def get_document_endpoint(
    document_id: UUID,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> DocumentRead:
    document = get_document(session, document_id)
    if document is None or document.is_archived:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return _to_read(document)


@router.post("/{document_id}/versions", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def add_document_version(
    document_id: UUID,
    payload: DocumentCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DocumentRead:
    document = get_document(session, document_id)
    if document is None or document.is_archived:
        raise HTTPException(status_code=404, detail="Документ не найден")
    try:
        create_document_version(
            session,
            document,
            payload.content,
            payload.variables,
            user.id,
            payload.change_summary,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    log_event(
        session,
        actor_id=user.id,
        entity_type="document",
        entity_id=document.id,
        action=AuditAction.VERSION,
        summary=f"Новая версия документа {document.title}",
    )
    session.commit()
    refreshed = get_document(session, document.id)
    assert refreshed is not None
    return _to_read(refreshed)


@router.post("/from-template/{template_id}", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_from_template(
    template_id: UUID,
    payload: DocumentFromTemplate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DocumentRead:
    template = session.get(DocumentTemplate, template_id)
    if template is None or template.is_archived:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    content = BuilderDocument.model_validate(template.content)
    create_payload = DocumentCreate(
        project_id=payload.project_id,
        template_id=template.id,
        doc_type=content.doc_type,
        title=payload.title or template.name,
        content=content,
        variables=payload.variables,
        change_summary="Создан из шаблона",
    )
    return create_document_endpoint(create_payload, session, user)


@router.get("/{document_id}/export/docx")
def export_document_docx(
    document_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    document = get_document(session, document_id)
    if document is None or document.is_archived:
        raise HTTPException(status_code=404, detail="Документ не найден")
    content = export_docx(_latest_builder_document(document))
    log_event(
        session,
        actor_id=user.id,
        entity_type="document",
        entity_id=document.id,
        action=AuditAction.EXPORT,
        summary=f"Экспорт DOCX: {document.title}",
        payload={"format": "docx"},
    )
    session.commit()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=_attachment_headers(document.title, "docx"),
    )


@router.get("/{document_id}/export/pdf")
def export_document_pdf(
    document_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    document = get_document(session, document_id)
    if document is None or document.is_archived:
        raise HTTPException(status_code=404, detail="Документ не найден")
    content = export_pdf(_latest_builder_document(document))
    log_event(
        session,
        actor_id=user.id,
        entity_type="document",
        entity_id=document.id,
        action=AuditAction.EXPORT,
        summary=f"Экспорт PDF: {document.title}",
        payload={"format": "pdf"},
    )
    session.commit()
    return Response(
        content=content,
        media_type="application/pdf",
        headers=_attachment_headers(document.title, "pdf"),
    )


@router.get("/{document_id}/export/html", response_class=HTMLResponse)
def export_document_html(
    document_id: UUID,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> HTMLResponse:
    document = get_document(session, document_id)
    if document is None or document.is_archived:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return HTMLResponse(export_html(_latest_builder_document(document)))


@router.post("/{document_id}/archive", response_model=DocumentRead)
def archive_document(
    document_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DocumentRead:
    document = get_document(session, document_id)
    if document is None or document.is_archived:
        raise HTTPException(status_code=404, detail="Документ не найден")
    document.is_archived = True
    log_event(
        session,
        actor_id=user.id,
        entity_type="document",
        entity_id=document.id,
        action=AuditAction.ARCHIVE,
        summary=f"Архивирован документ {document.title}",
    )
    session.commit()
    refreshed = get_document(session, document.id)
    assert refreshed is not None
    return _to_read(refreshed)
