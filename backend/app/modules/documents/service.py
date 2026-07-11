from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.documents.engine.builder_document import BuilderDocument
from app.modules.documents.engine.validators import validate_document_structure
from app.modules.documents.models import Document, DocumentStatus, DocumentVersion
from app.modules.documents.schemas import DocumentCreate
from app.modules.templates.models import DocumentTemplate


def create_document(session: Session, payload: DocumentCreate, user_id: UUID) -> Document:
    validate_document_structure(payload.content)
    if payload.template_id:
        template = session.get(DocumentTemplate, payload.template_id)
        if template is None or template.is_archived:
            raise ValueError("Шаблон не найден")
    document = Document(
        project_id=payload.project_id,
        template_id=payload.template_id,
        doc_type=payload.doc_type,
        title=payload.title,
        status=DocumentStatus.DRAFT,
        current_version=1,
        created_by_id=user_id,
    )
    version = DocumentVersion(
        version_number=1,
        content=payload.content.model_dump(),
        variables=payload.variables,
        change_summary=payload.change_summary or "Первоначальная версия",
        created_by_id=user_id,
    )
    document.versions.append(version)
    session.add(document)
    session.flush()
    return document


def create_document_version(
    session: Session,
    document: Document,
    content: BuilderDocument,
    variables: dict,
    user_id: UUID,
    change_summary: str | None,
) -> DocumentVersion:
    validate_document_structure(content)
    next_version = document.current_version + 1
    version = DocumentVersion(
        document_id=document.id,
        version_number=next_version,
        content=content.model_dump(),
        variables=variables,
        change_summary=change_summary or f"Версия {next_version}",
        created_by_id=user_id,
    )
    document.current_version = next_version
    session.add(version)
    session.flush()
    return version


def list_documents(session: Session) -> list[Document]:
    return list(
        session.scalars(
            select(Document)
            .where(Document.is_archived.is_(False))
            .options(selectinload(Document.versions))
            .order_by(Document.created_at.desc())
        )
    )


def get_document(session: Session, document_id: UUID) -> Document | None:
    return session.scalar(
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.versions))
    )
