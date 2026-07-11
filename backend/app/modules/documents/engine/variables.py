import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from jinja2 import Environment, StrictUndefined

from app.modules.documents.engine.builder_document import BuilderDocument, VariableDefinition

JINJA_ENV = Environment(undefined=StrictUndefined, autoescape=False)
VARIABLE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")


def flatten_context(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(flatten_context(value, path))
        else:
            flat[path] = value
            flat[key] = value
    return flat


def render_text(template: str, context: dict[str, Any]) -> str:
    merged = {**flatten_context(context), **context}
    return JINJA_ENV.from_string(template).render(**merged)


def render_document(document: BuilderDocument) -> BuilderDocument:
    rendered_sections = []
    for section in document.sections:
        rendered_sections.append(
            section.model_copy(update={"content": render_text(section.content, document.variables)})
        )
    return document.model_copy(update={"sections": rendered_sections})


def extract_variables(template: str) -> list[str]:
    return list(dict.fromkeys(VARIABLE_PATTERN.findall(template)))


def coerce_value(value: Any, var_type: str) -> Any:
    if value is None:
        return None
    if var_type == "string":
        return str(value)
    if var_type == "float":
        return float(Decimal(str(value)))
    if var_type == "date":
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))
    if var_type == "inn":
        return str(value)
    return value


def validate_variable_value(value: Any, definition: VariableDefinition) -> None:
    if definition.required and (value is None or value == ""):
        raise ValueError(f"Поле {definition.key} обязательно")
    if value is None or value == "":
        return
    if definition.var_type == "inn":
        inn = str(value)
        if not re.fullmatch(r"\d{10}(\d{2})?", inn):
            raise ValueError(f"Некорректный ИНН: {definition.key}")
    if definition.var_type == "float":
        try:
            float(Decimal(str(value)))
        except (InvalidOperation, ValueError) as error:
            raise ValueError(f"Поле {definition.key} должно быть числом") from error
    if definition.var_type == "date":
        if isinstance(value, date):
            return
        try:
            datetime.fromisoformat(str(value))
        except ValueError as error:
            raise ValueError(f"Поле {definition.key} должно быть датой") from error


def validate_variables(values: dict[str, Any], definitions: list[VariableDefinition]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for definition in definitions:
        value = values.get(definition.key)
        validate_variable_value(value, definition)
        if value not in (None, ""):
            normalized[definition.key] = coerce_value(value, definition.var_type)
    return normalized
