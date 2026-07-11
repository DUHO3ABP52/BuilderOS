from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.documents.engine.builder_document import BuilderDocument
from app.modules.memory.models import MemoryKind
from app.modules.memory.schemas import MemoryCreate
from app.modules.memory.service import remember
from app.modules.templates.models import DocumentTemplate


def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9а-яё]+", "-", value, flags=re.IGNORECASE)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value[:80] or "sample"


def suggest_slug(name: str) -> str:
    ascii_map = {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "c",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
    translit = "".join(ascii_map.get(ch, ch) for ch in name.lower())
    return _slugify(translit)


def learn_from_template_version(
    session: Session,
    *,
    parent: DocumentTemplate,
    new_template: DocumentTemplate,
    user_id: UUID,
) -> list[str]:
    """Сравнивает версии шаблона и сохраняет устойчивые правки в Memory."""
    old_doc = BuilderDocument.model_validate(parent.content)
    new_doc = BuilderDocument.model_validate(new_template.content)
    old_by_type = {section.section_type: section for section in old_doc.sections}
    notes: list[str] = []

    for section in new_doc.sections:
        previous = old_by_type.get(section.section_type)
        if previous is None:
            note = f"В шаблоне «{new_template.name}» добавлен раздел «{section.title}»."
        elif previous.content.strip() != section.content.strip():
            note = (
                f"В шаблоне «{new_template.name}» раздел «{section.title}» "
                f"({section.section_type}) обычно редактируется."
            )
        else:
            continue
        remember(
            session,
            MemoryCreate(
                kind=MemoryKind.PATTERN,
                key=f"template:{new_template.slug}:{section.section_type}",
                content=note,
                confidence=0.7,
                source="template_diff",
            ),
            user_id,
        )
        notes.append(note)

    if notes:
        remember(
            session,
            MemoryCreate(
                kind=MemoryKind.TEMPLATE_HINT,
                key=f"template:{new_template.slug}:hints",
                content=" | ".join(notes[:5]),
                confidence=0.8,
                source="template_diff",
            ),
            user_id,
        )
    return notes
