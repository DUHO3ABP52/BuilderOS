from datetime import date
from typing import Any

from app.modules.documents.engine.builder_document import BuilderDocument


def validate_document_period(starts_on: date | None, ends_on: date | None) -> None:
    if starts_on and ends_on and ends_on < starts_on:
        raise ValueError("Дата окончания не может быть раньше даты начала")


def validate_document_structure(document: BuilderDocument) -> None:
    if not document.title.strip():
        raise ValueError("У документа должно быть название")
    if not document.sections:
        raise ValueError("Документ должен содержать хотя бы одну секцию")


def validate_required_variables(document: BuilderDocument, required_keys: list[str]) -> None:
    missing = [key for key in required_keys if not document.variables.get(key)]
    if missing:
        raise ValueError(f"Не заполнены обязательные переменные: {', '.join(missing)}")


def validate_context(context: dict[str, Any]) -> None:
    validate_document_period(context.get("starts_on"), context.get("ends_on"))
