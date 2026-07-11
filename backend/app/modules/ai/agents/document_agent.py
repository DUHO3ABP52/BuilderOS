from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.documents.engine.builder_document import BuilderDocument, VariableDefinition
from app.modules.documents.schemas import DocumentCreate
from app.modules.documents.service import create_document
from app.modules.templates.models import DocumentTemplate
from app.modules.templates.service import list_templates

TEMPLATE_HINTS = [
    ("dogovor", ["договор", "подря", "контракт"]),
    ("act", ["акт", "кс-2", "кс2", "кс-3", "кс3"]),
    ("estimate", ["смет", "калькуляц"]),
    ("letter", ["письм", "уведомлен"]),
]


def _score_template(message: str, template: DocumentTemplate) -> int:
    text = message.lower()
    score = 0
    haystack = f"{template.name} {template.slug} {template.category} {template.description or ''}".lower()
    for token in re.findall(r"[а-яa-z0-9-]+", text):
        if len(token) > 3 and token in haystack:
            score += 2
    for slug_part, hints in TEMPLATE_HINTS:
        if any(hint in text for hint in hints) and (slug_part in template.slug or any(h in haystack for h in hints)):
            score += 5
    if template.slug == "dogovor-podryada" and any(h in text for h in ["договор", "подря"]):
        score += 3
    return score


def find_best_template(session: Session, message: str) -> DocumentTemplate | None:
    templates = list_templates(session)
    if not templates:
        return None
    ranked = sorted(templates, key=lambda item: _score_template(message, item), reverse=True)
    best = ranked[0]
    if _score_template(message, best) <= 0:
        return next((item for item in templates if item.slug == "dogovor-podryada"), templates[0])
    return best


def _get_by_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def missing_required_variables(template: DocumentTemplate, variables: dict[str, Any]) -> list[str]:
    definitions = [VariableDefinition.model_validate(item) for item in (template.variables or [])]
    missing: list[str] = []
    for definition in definitions:
        if not definition.required:
            continue
        value = variables.get(definition.key)
        if value in (None, ""):
            value = _get_by_path(variables, definition.key)
        if value in (None, ""):
            missing.append(definition.key)
    return missing


def create_draft_from_template(
    session: Session,
    *,
    template: DocumentTemplate,
    user_id: UUID,
    project_id: UUID | None,
    title: str | None,
    variables: dict[str, Any],
):
    content = BuilderDocument.model_validate(template.content)
    payload = DocumentCreate(
        project_id=project_id,
        template_id=template.id,
        doc_type=content.doc_type,
        title=title or template.name,
        content=content,
        variables=variables,
        change_summary="Создан AI Document Agent",
    )
    return create_document(session, payload, user_id)


def search_templates(session: Session, query: str) -> list[DocumentTemplate]:
    pattern = f"%{query}%"
    return list(
        session.scalars(
            select(DocumentTemplate).where(
                DocumentTemplate.is_archived.is_(False),
                or_(
                    DocumentTemplate.name.ilike(pattern),
                    DocumentTemplate.slug.ilike(pattern),
                    DocumentTemplate.description.ilike(pattern),
                ),
            )
        )
    )
