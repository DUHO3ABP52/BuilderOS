from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.documents.engine.sample_import import SampleImportResult, import_sample_to_builder_document
from app.modules.memory.learning import suggest_slug
from app.modules.templates.models import TemplateCategory
from app.modules.templates.schemas import TemplateCreate
from app.modules.templates.service import create_template
from app.services.storage import StorageService


CATEGORY_BY_DOC_TYPE = {
    "contract": TemplateCategory.CONTRACT,
    "act": TemplateCategory.ACT,
    "ks2": TemplateCategory.ACT,
    "ks3": TemplateCategory.ACT,
    "estimate": TemplateCategory.ESTIMATE,
}


def build_template_payload_from_sample(
    result: SampleImportResult,
    *,
    name: str | None = None,
    slug: str | None = None,
    category: str | None = None,
    description: str | None = None,
) -> TemplateCreate:
    resolved_name = name or result.document.title
    resolved_slug = slug or suggest_slug(resolved_name)
    if category:
        resolved_category = TemplateCategory(category)
    else:
        resolved_category = CATEGORY_BY_DOC_TYPE.get(result.document.doc_type, TemplateCategory.OTHER)
    return TemplateCreate(
        name=resolved_name,
        slug=resolved_slug,
        category=resolved_category,
        content=result.document.model_copy(update={"title": resolved_name}),
        variables=result.variables,
        description=description
        or (
            f"Шаблон из образца ({result.source_format}). "
            + ("; ".join(result.warnings) if result.warnings else "Переменные определены автоматически.")
        ),
    )


def import_sample_as_template(
    session: Session,
    *,
    data: bytes,
    filename: str | None,
    content_type: str | None,
    user_id: UUID,
    name: str | None = None,
    slug: str | None = None,
    category: str | None = None,
    store_original: bool = True,
):
    result = import_sample_to_builder_document(
        data,
        filename=filename,
        content_type=content_type,
        title=name,
    )
    payload = build_template_payload_from_sample(result, name=name, slug=slug, category=category)
    template = create_template(session, payload, user_id)

    storage_path = None
    if store_original and filename:
        try:
            storage_path = StorageService().put_bytes(
                f"samples/{template.id}/{filename}",
                data,
                content_type or "application/octet-stream",
            )
        except Exception:
            storage_path = None

    meta = dict(template.content.get("metadata") or {}) if isinstance(template.content, dict) else {}
    if isinstance(template.content, dict):
        meta.update(
            {
                "source_format": result.source_format,
                "source_filename": filename,
                "sample_values": result.sample_values,
                "warnings": result.warnings,
                "storage_path": storage_path,
            }
        )
        content = dict(template.content)
        content["metadata"] = meta
        template.content = content
        session.flush()

    return template, result
