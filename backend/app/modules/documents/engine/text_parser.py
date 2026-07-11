from __future__ import annotations

import re
from typing import Any

from app.modules.documents.engine.builder_document import BuilderDocument, BuilderSection, VariableDefinition

SECTION_MARKERS = {
    "шапка": "header",
    "преамбула": "header",
    "договор": "header",
    "предмет": "subject",
    "стоимость": "price",
    "цена": "price",
    "оплат": "payment",
    "порядок расчетов": "payment",
    "ответственность": "responsibility",
    "гарант": "guarantee",
    "форс": "force_majeure",
    "спор": "disputes",
    "приложение": "appendix",
    "реквизит": "requisites",
    "подпис": "signatures",
}

# kind helps special assignment rules
VARIABLE_SPECS: list[dict[str, str]] = [
    {"kind": "inn", "label": "ИНН", "var_type": "inn", "pattern": r"\bИНН[:\s]*(\d{10}(?:\d{2})?)\b"},
    {"kind": "kpp", "key": "customer.kpp", "label": "КПП", "var_type": "string", "pattern": r"\bКПП[:\s]*(\d{9})\b"},
    {
        "kind": "ogrn",
        "key": "customer.ogrn",
        "label": "ОГРН",
        "var_type": "string",
        "pattern": r"\bОГРН[:\s]*(\d{13}(?:\d{2})?)\b",
    },
    {
        "kind": "contract_number",
        "key": "contract.number",
        "label": "Номер договора",
        "var_type": "string",
        "pattern": r"(?:Договор|ДОГОВОР)\s*№\s*([A-Za-zА-Яа-я0-9\-/]+)",
    },
    {
        "kind": "date",
        "key": "contract.date",
        "label": "Дата договора",
        "var_type": "date",
        "pattern": r"\b(\d{2}\.\d{2}\.\d{4})\b",
    },
    {
        "kind": "price",
        "key": "contract.price",
        "label": "Стоимость",
        "var_type": "float",
        "pattern": r"\b(\d{1,3}(?:[ \u00a0]\d{3})*(?:[.,]\d{2})?)\s*(?:руб\.?|₽)",
    },
    {
        "kind": "address",
        "key": "project.address",
        "label": "Адрес объекта",
        "var_type": "string",
        "pattern": r"(?:адрес[:\s]+)(.{10,120}?)(?:\.|$)",
    },
    {
        "kind": "project",
        "key": "project.name",
        "label": "Название объекта",
        "var_type": "string",
        "pattern": r"(?:объект[ае]?[:\s«\"]+)([^»\"\n]{3,120})",
    },
    {
        "kind": "customer",
        "key": "customer.name",
        "label": "Заказчик",
        "var_type": "string",
        "pattern": r"(?:Заказчик[:\s]+)((?:ООО|АО|ПАО|ИП)[^,\n]{3,120})",
    },
    {
        "kind": "contractor",
        "key": "contractor.name",
        "label": "Подрядчик",
        "var_type": "string",
        "pattern": r"(?:Подрядчик[:\s]+)((?:ООО|АО|ПАО|ИП)[^,\n]{3,120})",
    },
]


def _detect_section_type(title: str) -> str:
    lowered = title.lower()
    for marker, section_type in SECTION_MARKERS.items():
        if marker in lowered:
            return section_type
    return "generic"


def _is_heading(line: str) -> bool:
    compact = line.strip()
    if not compact or len(compact) > 120:
        return False
    if compact.isupper() and len(compact) >= 3:
        return True
    if re.match(r"^\d+(\.\d+)*\.?\s+\S+", compact):
        return True
    if compact.startswith("§") or compact.lower().startswith("раздел"):
        return True
    return False


def parse_plain_text(text: str, *, title: str | None = None, doc_type: str = "imported") -> BuilderDocument:
    lines = [line.strip() for line in (text or "").replace("\r\n", "\n").split("\n")]
    lines = [line for line in lines if line]
    sections: list[BuilderSection] = []
    current_title = "Преамбула"
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_title, current_lines
        if not current_lines:
            return
        sections.append(
            BuilderSection(
                title=current_title,
                section_type=_detect_section_type(current_title),
                content="\n".join(current_lines).strip(),
            )
        )
        current_title = "Преамбула"
        current_lines = []

    for line in lines:
        if _is_heading(line) and current_lines:
            flush()
            current_title = line
            continue
        if _is_heading(line) and not current_lines:
            current_title = line
            continue
        current_lines.append(line)
    flush()

    if not sections:
        sections.append(BuilderSection(title="Содержание", section_type="generic", content=(text or "").strip()))

    resolved_title = title or sections[0].title or "Импортированный образец"
    return BuilderDocument(title=resolved_title, doc_type=doc_type, sections=sections, variables={}, metadata={})


def detect_doc_type(text: str) -> str:
    lowered = (text or "").lower()
    if "кс-2" in lowered or "кс2" in lowered:
        return "ks2"
    if "кс-3" in lowered or "кс3" in lowered:
        return "ks3"
    if "смет" in lowered:
        return "estimate"
    if "акт" in lowered:
        return "act"
    if "договор" in lowered or "подря" in lowered:
        return "contract"
    return "imported"


def extract_variables_from_text(text: str) -> tuple[str, list[VariableDefinition], dict[str, Any]]:
    replacements: list[tuple[int, int, str, str, VariableDefinition]] = []
    definitions: dict[str, VariableDefinition] = {}
    values: dict[str, Any] = {}
    inn_count = 0

    for spec in VARIABLE_SPECS:
        matches = list(re.finditer(spec["pattern"], text, flags=re.IGNORECASE))
        if not matches:
            continue
        for match in matches:
            raw = match.group(1).strip()
            if spec["kind"] == "inn":
                inn_count += 1
                key = "customer.inn" if inn_count == 1 else "contractor.inn"
                label = "ИНН заказчика" if inn_count == 1 else "ИНН подрядчика"
                if inn_count > 2:
                    break
            else:
                key = spec["key"]
                label = spec["label"]
            if key in definitions:
                continue
            definition = VariableDefinition(key=key, var_type=spec["var_type"], required=True, label=label)
            definitions[key] = definition
            cleaned = raw.replace(" ", "").replace("\u00a0", "") if spec["var_type"] == "float" else raw
            values[key] = cleaned
            replacements.append((match.start(1), match.end(1), key, cleaned, definition))
            if spec["kind"] != "inn":
                break

    replacements.sort(key=lambda item: item[0], reverse=True)
    result = text
    for start, end, key, _value, _definition in replacements:
        result = result[:start] + "{{" + key + "}}" + result[end:]
    return result, list(definitions.values()), values


def templatize_document(document: BuilderDocument) -> tuple[BuilderDocument, list[VariableDefinition], dict[str, Any]]:
    all_defs: dict[str, VariableDefinition] = {}
    sample_values: dict[str, Any] = {}
    new_sections: list[BuilderSection] = []
    for section in document.sections:
        content, defs, values = extract_variables_from_text(section.content)
        new_sections.append(section.model_copy(update={"content": content}))
        for item in defs:
            all_defs.setdefault(item.key, item)
        for key, value in values.items():
            sample_values.setdefault(key, value)

    full_text = "\n".join(section.content for section in document.sections)
    templated = document.model_copy(
        update={
            "sections": new_sections,
            "doc_type": document.doc_type if document.doc_type != "imported" else detect_doc_type(full_text),
            "metadata": {
                **(document.metadata or {}),
                "templatized": True,
                "sample_values": sample_values,
            },
        }
    )
    return templated, list(all_defs.values()), sample_values
