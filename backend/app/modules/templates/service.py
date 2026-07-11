from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.documents.engine.builder_document import VariableDefinition
from app.modules.documents.engine.validators import validate_document_structure
from app.modules.templates.models import DocumentTemplate
from app.modules.templates.schemas import TemplateCreate


def create_template(session: Session, payload: TemplateCreate, user_id: UUID) -> DocumentTemplate:
    validate_document_structure(payload.content)
    template = DocumentTemplate(
        name=payload.name,
        slug=payload.slug,
        category=payload.category.value,
        version=1,
        content=payload.content.model_dump(),
        variables=[item.model_dump() for item in payload.variables],
        description=payload.description,
        created_by_id=user_id,
    )
    session.add(template)
    session.flush()
    return template


def create_template_version(
    session: Session,
    parent: DocumentTemplate,
    payload: TemplateCreate,
    user_id: UUID,
) -> DocumentTemplate:
    validate_document_structure(payload.content)
    latest_version = session.scalar(
        select(DocumentTemplate.version)
        .where(DocumentTemplate.slug == parent.slug)
        .order_by(DocumentTemplate.version.desc())
        .limit(1)
    )
    template = DocumentTemplate(
        name=payload.name,
        slug=parent.slug,
        category=payload.category.value,
        version=(latest_version or parent.version) + 1,
        parent_id=parent.id,
        content=payload.content.model_dump(),
        variables=[item.model_dump() for item in payload.variables],
        description=payload.description,
        created_by_id=user_id,
    )
    session.add(template)
    session.flush()
    return template


def list_templates(session: Session) -> list[DocumentTemplate]:
    return list(
        session.scalars(
            select(DocumentTemplate)
            .where(DocumentTemplate.is_archived.is_(False))
            .order_by(DocumentTemplate.slug, DocumentTemplate.version.desc())
        )
    )
