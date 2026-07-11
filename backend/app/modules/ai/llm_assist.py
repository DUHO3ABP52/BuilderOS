from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.core.config import settings
from app.modules.ai.schemas import IntentName
from app.modules.knowledge.models import KnowledgeItem
from app.services import llm as llm_service

logger = logging.getLogger(__name__)

_VALID_INTENTS = {item.value for item in IntentName}

_CLASSIFY_SYSTEM = """Ты классификатор намерений для BuilderOS — локальной ОС строительного ИП.
Ответь ТОЛЬКО одним JSON-объектом без markdown:
{"intent":"<имя>","query":"<краткий поисковый/содержательный фрагмент>"}

Допустимые intent:
- create_document — создать договор/акт/смету/документ из шаблона
- search_knowledge — поиск по СП/СНиП/ГОСТ/базе знаний
- remember — сохранить факт в память
- recall — вспомнить сохранённые факты
- create_task — создать задачу
- list_tasks — список открытых задач
- help — справка по командам
- unknown — неясно

Правила:
- query: суть без служебных слов («найди», «сделай», «запомни»), на русском
- не выдумывай данные объектов и контрагентов
- документы только из шаблонов, не генерируй текст договора сам
"""

_KNOWLEDGE_SYSTEM = """Ты помощник строительного ИП в BuilderOS.
Отвечай по-русски кратко и по делу, опираясь ТОЛЬКО на переданные фрагменты базы знаний.
Если в фрагментах нет ответа — прямо скажи, что в базе этого нет.
Не выдумывай номера ГОСТ/СП и формулировки норм.
Не давай юридических гарантий — это справочная помощь, не замена юриста.
"""


def classify_intent_with_llm(message: str) -> tuple[IntentName, str] | None:
    if not llm_service.llm_is_configured():
        return None
    try:
        raw = llm_service.chat(
            [
                {"role": "system", "content": _CLASSIFY_SYSTEM},
                {"role": "user", "content": message.strip()},
            ],
            temperature=0.0,
            max_tokens=200,
        )
    except llm_service.LLMError:
        return None

    data = _parse_json_object(raw)
    if not data:
        return None
    intent_raw = str(data.get("intent", "")).strip().lower()
    if intent_raw not in _VALID_INTENTS:
        return None
    query = str(data.get("query") or message).strip()
    return IntentName(intent_raw), query


def synthesize_knowledge_answer(query: str, items: list[KnowledgeItem]) -> str | None:
    if not items or not llm_service.llm_is_configured():
        return None

    chunks: list[str] = []
    for item in items[:6]:
        excerpt = (item.content or "")[:1200]
        chunks.append(f"### {item.title} [{item.category}]\n{excerpt}")
    context = "\n\n".join(chunks)
    user = f"Вопрос пользователя: {query}\n\nФрагменты базы знаний:\n{context}"
    try:
        return llm_service.chat(
            [
                {"role": "system", "content": _KNOWLEDGE_SYSTEM},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=800,
            allow_cloud=settings.llm_cloud_for_knowledge,
        )
    except llm_service.LLMError:
        logger.info("Knowledge synthesis skipped: LLM unavailable")
        return None


def draft_clarification(message: str) -> str | None:
    """Мягкая подсказка, когда правило и LLM не уверены в намерении."""
    if not llm_service.llm_is_configured():
        return None
    try:
        return llm_service.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "Ты координатор BuilderOS. Пользователь написал неясный запрос. "
                        "Кратко по-русски (2–4 предложения) предложи, что можно сделать: "
                        "договор из шаблона, поиск ГОСТ/СП, задача, запомнить факт. "
                        "Не выдумывай данные и не создавай документы."
                    ),
                },
                {"role": "user", "content": message.strip()},
            ],
            temperature=0.3,
            max_tokens=300,
        )
    except llm_service.LLMError:
        return None


def _parse_json_object(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None
