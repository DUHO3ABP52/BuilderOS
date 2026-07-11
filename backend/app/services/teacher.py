from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.memory.models import MemoryKind
from app.modules.memory.schemas import MemoryCreate
from app.modules.memory.service import remember
from app.services import llm as llm_service
from app.services.llm import LLMError

_TEACHER_SYSTEM = (
    "Ты учитель-консультант для строительного ИП в России.\n"
    "Отвечай кратко по-русски: типовые формулировки, обычная практика, "
    "на что обратить внимание.\n"
    "Не выдумывай конкретные ИНН, адреса, суммы, номера договоров и реквизиты.\n"
    "Не утверждай юридическую силу ответа — это справочный паттерн, не замена юристу.\n"
    "Структура ответа:\n"
    "1) Краткий ответ\n"
    "2) Типовая формулировка (если уместно)\n"
    "3) Риски / что проверить локально\n"
)


@dataclass(frozen=True)
class TeacherResult:
    sanitized_question: str
    answer: str
    redactions: list[str]
    saved: bool
    memory_id: UUID | None = None
    endpoint: str | None = None


def sanitize_for_teacher(text: str) -> tuple[str, list[str]]:
    """Убирает ПДн/реквизиты перед отправкой учителю в облако."""
    redactions: list[str] = []
    cleaned = text.strip()

    def _mark(label: str) -> None:
        if label not in redactions:
            redactions.append(label)

    cleaned, n = re.subn(r"\b\d{12}\b", "[ИНН]", cleaned)
    if n:
        _mark("inn_12")
    cleaned, n = re.subn(r"\b\d{10}\b", "[ИНН]", cleaned)
    if n:
        _mark("inn_10")
    cleaned, n = re.subn(r"\b\d{20}\b", "[СЧЁТ]", cleaned)
    if n:
        _mark("account")
    cleaned, n = re.subn(
        r"\b(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b",
        "[ТЕЛЕФОН]",
        cleaned,
    )
    if n:
        _mark("phone")
    cleaned, n = re.subn(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", "[EMAIL]", cleaned)
    if n:
        _mark("email")
    cleaned, n = re.subn(
        r"\b\d{1,3}(?:[ \u00a0]\d{3})+(?:[.,]\d{2})?\b|\b\d+(?:[.,]\d{2})?\s*(?:руб|₽|RUB)\b",
        "[СУММА]",
        cleaned,
        flags=re.IGNORECASE,
    )
    if n:
        _mark("amount")
    cleaned, n = re.subn(
        r"(?:ООО|АО|ПАО|ИП)\s+[«\"]?[\wА-Яа-яЁё\-.\s]{2,60}[»\"]?",
        "[КОМПАНИЯ]",
        cleaned,
    )
    if n:
        _mark("company")
    cleaned, n = re.subn(r"№\s*[\w\-./]+", "№ [НОМЕР]", cleaned)
    if n:
        _mark("doc_number")

    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned, redactions


def ask_teacher(question: str) -> tuple[str, str]:
    """Возвращает (answer, endpoint_name)."""
    if not settings.llm_teacher_enabled:
        raise LLMError("Teacher-контур отключён (LLM_TEACHER_ENABLED=false)")
    if not settings.llm_cloud_for_teacher:
        raise LLMError("Облачный учитель запрещён (LLM_CLOUD_FOR_TEACHER=false)")
    if not llm_service.llm_is_configured():
        raise LLMError("LLM отключена")

    if len(question.strip()) < 8:
        raise LLMError("Вопрос слишком короткий")

    answer = llm_service.chat_teacher(
        [
            {"role": "system", "content": _TEACHER_SYSTEM},
            {"role": "user", "content": question.strip()},
        ],
        temperature=0.2,
        max_tokens=900,
    )
    return answer, "teacher"


def learn_from_teacher(
    session: Session,
    *,
    question: str,
    user_id: UUID,
    project_id: UUID | None = None,
    save: bool = False,
    topic: str | None = None,
) -> TeacherResult:
    sanitized, redactions = sanitize_for_teacher(question)
    if len(sanitized) < 8:
        raise ValueError("После обезличивания вопрос слишком короткий. Уберите реквизиты и уточните тему.")

    answer, endpoint = ask_teacher(sanitized)
    memory_id = None
    saved = False
    should_save = save or settings.llm_teacher_auto_save
    if should_save:
        key_base = (topic or sanitized)[:60].strip().lower().replace(" ", "-") or "teacher-pattern"
        fact = remember(
            session,
            MemoryCreate(
                kind=MemoryKind.PATTERN,
                key=f"teacher:{key_base}",
                content=f"Вопрос: {sanitized}\n\nПаттерн учителя:\n{answer}",
                confidence=settings.llm_teacher_confidence,
                source="teacher",
                project_id=project_id,
            ),
            user_id,
        )
        memory_id = fact.id
        saved = True

    return TeacherResult(
        sanitized_question=sanitized,
        answer=answer,
        redactions=redactions,
        saved=saved,
        memory_id=memory_id,
        endpoint=endpoint,
    )
