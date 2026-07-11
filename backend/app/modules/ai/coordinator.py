from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.ai.agents import (
    calendar_agent,
    document_agent,
    finance_agent,
    graph_agent,
    knowledge_agent,
    memory_agent,
    task_agent,
    teacher_agent,
)
from app.modules.ai import llm_assist
from app.modules.ai.schemas import AgentName, AssistantAction, AssistantRequest, AssistantResponse, IntentName
from app.modules.events.models import AuditAction
from app.modules.events.service import log_event
from app.services.llm import LLMError


def classify_intent(message: str) -> IntentName:
    text = message.lower().strip()
    if any(token in text for token in ["помощь", "что умеешь", "help", "команды"]):
        return IntentName.HELP
    if any(
        token in text
        for token in [
            "спроси учителя",
            "спроси облако",
            "спроси у учителя",
            "научись",
            "как принято",
            "как обычно формулир",
            "что обычно пишут",
            "teacher",
        ]
    ):
        return IntentName.ASK_TEACHER
    if any(token in text for token in ["запомни", "запомнить", "учти что"]):
        return IntentName.REMEMBER
    if any(token in text for token in ["что ты помнишь", "вспомни", "память"]):
        return IntentName.RECALL
    if any(
        token in text
        for token in [
            "граф",
            "контекст объекта",
            "что связано с",
            "связи объекта",
            "по объекту",
            "расскажи про объект",
            "что известно об объекте",
        ]
    ):
        return IntentName.PROJECT_CONTEXT
    if any(token in text for token in ["баланс", "сводка по финанс", "финансов", "сколько получили", "сколько потратили"]):
        return IntentName.FINANCE_SUMMARY
    if any(token in text for token in ["платёж", "платеж", "оплат", "аванс", "счет на", "счёт на"]):
        if any(token in text for token in ["покажи", "список", "открыт", "ожида"]):
            return IntentName.LIST_PAYMENTS
        if any(token in text for token in ["добавь", "создай", "запиши", "внеси"]):
            return IntentName.CREATE_PAYMENT
        return IntentName.LIST_PAYMENTS
    if any(token in text for token in ["календар", "встреч", "событи", "выезд", "созвон"]):
        if any(token in text for token in ["покажи", "список", "ближайш", "что на"]):
            return IntentName.LIST_EVENTS
        if any(token in text for token in ["добавь", "создай", "поставь", "назначь"]):
            return IntentName.CREATE_EVENT
        return IntentName.LIST_EVENTS
    if any(token in text for token in ["задач", "напомни", "todo", "сделать список"]):
        if any(token in text for token in ["покажи", "список", "открыт"]):
            return IntentName.LIST_TASKS
        if any(token in text for token in ["создай", "добавь", "поставь", "напомни"]):
            return IntentName.CREATE_TASK
        return IntentName.LIST_TASKS
    if any(token in text for token in ["сп ", "снип", "гост", "норм", "найди в базе", "база знаний", "что говорит"]):
        return IntentName.SEARCH_KNOWLEDGE
    if any(
        token in text
        for token in ["договор", "акт", "смет", "кс-2", "кс2", "кс-3", "документ", "шаблон", "подготов"]
    ):
        return IntentName.CREATE_DOCUMENT
    if text.startswith("найди") or text.startswith("поиск"):
        return IntentName.SEARCH_KNOWLEDGE
    return IntentName.UNKNOWN


def resolve_intent(message: str) -> tuple[IntentName, str | None]:
    """Сначала правила (быстро и предсказуемо), LLM — только для неизвестных фраз."""
    intent = classify_intent(message)
    if intent != IntentName.UNKNOWN:
        return intent, None
    llm_result = llm_assist.classify_intent_with_llm(message)
    if llm_result is None:
        return IntentName.UNKNOWN, None
    return llm_result[0], llm_result[1]


def _extract_after(message: str, markers: list[str]) -> str:
    lower = message.lower()
    for marker in markers:
        index = lower.find(marker)
        if index >= 0:
            return message[index + len(marker) :].strip(" :,-")
    return message.strip()


def handle_assistant(session: Session, user_id: UUID, payload: AssistantRequest) -> AssistantResponse:
    intent, llm_query = resolve_intent(payload.message)
    if intent == IntentName.HELP:
        return AssistantResponse(
            reply=(
                "Я координатор BuilderOS. Могу:\n"
                "• подготовить документ («сделай договор»)\n"
                "• искать по базе знаний («найди СП»)\n"
                "• задачи («добавь задачу…»)\n"
                "• платежи («добавь платёж аванс 150000», «баланс»)\n"
                "• календарь («добавь встречу завтра», «что в календаре»)\n"
                "• граф объекта («контекст объекта», «что связано с объектом»)\n"
                "• учитель («спроси учителя: как обычно формулируют гарантию»)\n"
                "• память («запомни: …»)"
            ),
            intent=intent,
            agent=AgentName.COORDINATOR,
        )

    if intent == IntentName.CREATE_DOCUMENT:
        return _handle_document(session, user_id, payload)
    if intent == IntentName.SEARCH_KNOWLEDGE:
        return _handle_knowledge(session, user_id, payload, llm_query=llm_query)
    if intent == IntentName.REMEMBER:
        return _handle_remember(session, user_id, payload)
    if intent == IntentName.RECALL:
        return _handle_recall(session, payload)
    if intent == IntentName.PROJECT_CONTEXT:
        return _handle_project_context(session, payload)
    if intent == IntentName.ASK_TEACHER:
        return _handle_ask_teacher(session, user_id, payload)
    if intent == IntentName.CREATE_TASK:
        return _handle_create_task(session, user_id, payload)
    if intent == IntentName.LIST_TASKS:
        return _handle_list_tasks(session)
    if intent == IntentName.CREATE_PAYMENT:
        return _handle_create_payment(session, user_id, payload)
    if intent == IntentName.LIST_PAYMENTS:
        return _handle_list_payments(session)
    if intent == IntentName.FINANCE_SUMMARY:
        return _handle_finance_summary(session)
    if intent == IntentName.CREATE_EVENT:
        return _handle_create_event(session, user_id, payload)
    if intent == IntentName.LIST_EVENTS:
        return _handle_list_events(session)

    hint = llm_assist.draft_clarification(payload.message)
    return AssistantResponse(
        reply=hint
        or (
            "Не уверен, что сделать. Попробуйте: «сделай договор», «найди ГОСТ», "
            "«спроси учителя: …», «контекст объекта» или «помощь»."
        ),
        intent=IntentName.UNKNOWN,
        agent=AgentName.COORDINATOR,
        status="needs_clarification",
        actions=[
            AssistantAction(
                type="ask_teacher",
                label="Спросить учителя (облако, обезличенно)",
                payload={"message": payload.message},
            )
        ],
    )


def _handle_document(session: Session, user_id: UUID, payload: AssistantRequest) -> AssistantResponse:
    template = document_agent.find_best_template(session, payload.message)
    if template is None:
        return AssistantResponse(
            reply="Шаблоны ещё не загружены. Добавьте шаблон в реестр и повторите запрос.",
            intent=IntentName.CREATE_DOCUMENT,
            agent=AgentName.DOCUMENT,
            status="error",
        )

    missing = document_agent.missing_required_variables(template, payload.variables)
    hints = memory_agent.recall_template_hints(session, template.slug)
    hint_text = ("\nПодсказки из памяти правок:\n- " + "\n- ".join(hints)) if hints else ""
    if missing and not payload.confirm:
        labels = ", ".join(missing)
        return AssistantResponse(
            reply=(
                f"Нашёл шаблон «{template.name}» (v{template.version}). "
                f"Не хватает данных: {labels}. Передайте variables и повторите запрос "
                "или подтвердите создание черновика с частичными данными (confirm=true)."
                f"{hint_text}"
            ),
            intent=IntentName.CREATE_DOCUMENT,
            agent=AgentName.DOCUMENT,
            status="needs_data",
            missing_fields=missing,
            data={
                "template_id": str(template.id),
                "template_name": template.name,
                "learning_hints": hints,
            },
            actions=[
                AssistantAction(
                    type="fill_variables",
                    label="Заполнить переменные и создать",
                    payload={"template_id": str(template.id), "missing_fields": missing},
                )
            ],
        )

    document = document_agent.create_draft_from_template(
        session,
        template=template,
        user_id=user_id,
        project_id=payload.project_id,
        title=None,
        variables=payload.variables,
    )
    log_event(
        session,
        actor_id=user_id,
        entity_type="document",
        entity_id=document.id,
        action=AuditAction.CREATE,
        summary=f"AI создал черновик: {document.title}",
        payload={"agent": "document", "template_id": str(template.id)},
    )
    task_agent.create_task_from_text(
        session,
        title=f"Проверить документ: {document.title}",
        user_id=user_id,
        project_id=payload.project_id,
        description="Черновик создан Document Agent. Нужна проверка перед экспортом.",
    )
    session.commit()
    return AssistantResponse(
        reply=(
            f"Создал черновик «{document.title}» из шаблона «{template.name}». "
            "Добавил задачу на проверку. Можно экспортировать в DOCX/PDF."
            f"{hint_text}"
        ),
        intent=IntentName.CREATE_DOCUMENT,
        agent=AgentName.DOCUMENT,
        data={
            "document_id": str(document.id),
            "template_id": str(template.id),
            "current_version": document.current_version,
            "learning_hints": hints,
        },
        actions=[
            AssistantAction(
                type="export_docx",
                label="Экспорт DOCX",
                payload={"document_id": str(document.id)},
            ),
            AssistantAction(
                type="open_document",
                label="Открыть документ",
                payload={"document_id": str(document.id)},
            ),
        ],
        missing_fields=missing,
    )


def _handle_knowledge(
    session: Session,
    user_id: UUID,
    payload: AssistantRequest,
    *,
    llm_query: str | None = None,
) -> AssistantResponse:
    if llm_query:
        query = llm_query
    else:
        query = _extract_after(payload.message, ["найди", "поиск", "что говорит", "база знаний"])
        query = (
            re.sub(r"^(в\s+)?(базе\s+знаний|сп|снип|гост)\s*", "", query, flags=re.IGNORECASE).strip()
            or payload.message
        )
    items = knowledge_agent.search_knowledge(session, query)
    ranked = knowledge_agent.search_knowledge_ranked(session, query)
    log_event(
        session,
        actor_id=user_id,
        entity_type="knowledge",
        entity_id=None,
        action=AuditAction.UPDATE,
        summary=f"AI поиск по знаниям: {query[:120]}",
        payload={
            "agent": "knowledge",
            "found": len(ranked),
            "sources": list({row.source for row in ranked}),
        },
    )
    session.commit()
    if not ranked:
        return AssistantResponse(
            reply=f"По запросу «{query}» в базе знаний ничего не нашёл. Добавьте СП/ГОСТ в раздел знаний.",
            intent=IntentName.SEARCH_KNOWLEDGE,
            agent=AgentName.KNOWLEDGE,
            status="empty",
            data={"query": query},
        )
    lines = [
        f"• {row.item.title} [{row.item.category}]"
        + (f" · score={row.score:.2f}" if row.score is not None else f" · {row.source}")
        for row in ranked[:8]
    ]
    synthesized = llm_assist.synthesize_knowledge_answer(query, [row.item for row in ranked])
    reply = synthesized if synthesized else ("Нашёл в базе знаний:\n" + "\n".join(lines))
    return AssistantResponse(
        reply=reply,
        intent=IntentName.SEARCH_KNOWLEDGE,
        agent=AgentName.KNOWLEDGE,
        data={
            "query": query,
            "llm_used": bool(synthesized),
            "rag_used": any(row.source == "rag" for row in ranked),
            "items": [
                {
                    "id": str(row.item.id),
                    "title": row.item.title,
                    "category": row.item.category,
                    "excerpt": (row.chunk or row.item.content)[:240],
                    "score": row.score,
                    "source": row.source,
                }
                for row in ranked[:8]
            ],
        },
    )


def _handle_remember(session: Session, user_id: UUID, payload: AssistantRequest) -> AssistantResponse:
    text = _extract_after(payload.message, ["запомни", "запомнить", "учти что"])
    if not text:
        return AssistantResponse(
            reply="Что именно запомнить? Например: «запомни: гарантия всегда 24 месяца».",
            intent=IntentName.REMEMBER,
            agent=AgentName.MEMORY,
            status="needs_data",
        )
    fact = memory_agent.remember_text(session, text, user_id, payload.project_id)
    log_event(
        session,
        actor_id=user_id,
        entity_type="memory",
        entity_id=fact.id,
        action=AuditAction.CREATE,
        summary=f"AI запомнил: {fact.key}",
    )
    session.commit()
    return AssistantResponse(
        reply=f"Запомнил: {fact.content}",
        intent=IntentName.REMEMBER,
        agent=AgentName.MEMORY,
        data={"memory_id": str(fact.id), "key": fact.key},
    )


def _handle_recall(session: Session, payload: AssistantRequest) -> AssistantResponse:
    query = _extract_after(payload.message, ["вспомни", "что ты помнишь", "память"])
    facts = memory_agent.recall_text(
        session,
        query if query and query != payload.message else None,
        project_id=payload.project_id,
    )
    if not facts:
        return AssistantResponse(
            reply="Пока ничего не помню. Скажите «запомни: …», и я сохраню факт.",
            intent=IntentName.RECALL,
            agent=AgentName.MEMORY,
            status="empty",
        )
    lines = [f"• {fact.content}" for fact in facts[:10]]
    return AssistantResponse(
        reply="Вот что помню:\n" + "\n".join(lines),
        intent=IntentName.RECALL,
        agent=AgentName.MEMORY,
        data={"items": [{"id": str(fact.id), "key": fact.key, "content": fact.content} for fact in facts[:10]]},
    )


def _handle_project_context(session: Session, payload: AssistantRequest) -> AssistantResponse:
    reply, data = graph_agent.project_context(session, payload.project_id, payload.message)
    status = "ok" if data else "needs_data"
    return AssistantResponse(
        reply=reply,
        intent=IntentName.PROJECT_CONTEXT,
        agent=AgentName.GRAPH,
        status=status,
        missing_fields=[] if data else ["project_id"],
        data=data,
    )


def _handle_ask_teacher(session: Session, user_id: UUID, payload: AssistantRequest) -> AssistantResponse:
    question = _extract_after(
        payload.message,
        [
            "спроси учителя",
            "спроси у учителя",
            "спроси облако",
            "научись",
            "как принято",
            "как обычно формулируют",
            "что обычно пишут",
            "teacher",
        ],
    )
    question = question or payload.message
    try:
        result = teacher_agent.ask(
            session,
            question,
            user_id,
            project_id=payload.project_id,
            save=payload.confirm,
        )
    except ValueError as error:
        return AssistantResponse(
            reply=str(error),
            intent=IntentName.ASK_TEACHER,
            agent=AgentName.TEACHER,
            status="needs_data",
        )
    except LLMError as error:
        return AssistantResponse(
            reply=(
                f"Учитель недоступен: {error}. "
                "Нужны OmniRoute (`docker compose --profile omniroute up`) и "
                "LLM_CLOUD_FOR_TEACHER=true."
            ),
            intent=IntentName.ASK_TEACHER,
            agent=AgentName.TEACHER,
            status="error",
        )

    if result.saved:
        log_event(
            session,
            actor_id=user_id,
            entity_type="memory",
            entity_id=result.memory_id,
            action=AuditAction.CREATE,
            summary="Сохранён PATTERN от учителя",
        )
        session.commit()
        reply = (
            "Обезличенный вопрос учителю:\n"
            f"«{result.sanitized_question}»\n\n"
            f"{result.answer}\n\n"
            "Сохранил как локальный PATTERN (source=teacher). "
            "Это справочный паттерн, не готовый документ."
        )
        status = "ok"
        actions: list[AssistantAction] = []
    else:
        session.rollback()
        reply = (
            "Обезличенный вопрос учителю:\n"
            f"«{result.sanitized_question}»\n\n"
            f"{result.answer}\n\n"
            "Ответ ещё не сохранён. Повторите запрос с confirm=true, "
            "чтобы записать PATTERN в локальную память."
        )
        status = "needs_confirmation"
        actions = [
            AssistantAction(
                type="save_teacher_pattern",
                label="Сохранить паттерн локально",
                payload={"message": payload.message, "confirm": True, "project_id": str(payload.project_id) if payload.project_id else None},
            )
        ]

    return AssistantResponse(
        reply=reply,
        intent=IntentName.ASK_TEACHER,
        agent=AgentName.TEACHER,
        status=status,
        actions=actions,
        data={
            "sanitized_question": result.sanitized_question,
            "redactions": result.redactions,
            "saved": result.saved,
            "memory_id": str(result.memory_id) if result.memory_id else None,
            "answer": result.answer,
        },
    )


def _handle_create_task(session: Session, user_id: UUID, payload: AssistantRequest) -> AssistantResponse:
    title = _extract_after(payload.message, ["добавь задачу", "создай задачу", "поставь задачу", "напомни", "задача"])
    title = title or payload.message
    task = task_agent.create_task_from_text(session, title, user_id, payload.project_id)
    log_event(
        session,
        actor_id=user_id,
        entity_type="task",
        entity_id=task.id,
        action=AuditAction.CREATE,
        summary=f"AI создал задачу: {task.title}",
    )
    session.commit()
    return AssistantResponse(
        reply=f"Создал задачу: {task.title}",
        intent=IntentName.CREATE_TASK,
        agent=AgentName.TASK,
        data={"task_id": str(task.id), "title": task.title, "status": task.status},
    )


def _handle_list_tasks(session: Session) -> AssistantResponse:
    tasks = task_agent.open_tasks(session)
    if not tasks:
        return AssistantResponse(
            reply="Открытых задач нет.",
            intent=IntentName.LIST_TASKS,
            agent=AgentName.TASK,
            status="empty",
        )
    lines = [f"• [{task.status}] {task.title}" for task in tasks[:15]]
    return AssistantResponse(
        reply="Открытые задачи:\n" + "\n".join(lines),
        intent=IntentName.LIST_TASKS,
        agent=AgentName.TASK,
        data={"tasks": [{"id": str(task.id), "title": task.title, "status": task.status} for task in tasks[:15]]},
    )


def _handle_create_payment(session: Session, user_id: UUID, payload: AssistantRequest) -> AssistantResponse:
    try:
        payment = finance_agent.create_payment_from_text(session, payload.message, user_id, payload.project_id)
    except ValueError as error:
        return AssistantResponse(
            reply=str(error),
            intent=IntentName.CREATE_PAYMENT,
            agent=AgentName.FINANCE,
            status="needs_data",
            missing_fields=["amount"],
        )
    log_event(
        session,
        actor_id=user_id,
        entity_type="payment",
        entity_id=payment.id,
        action=AuditAction.CREATE,
        summary=f"AI создал платёж: {payment.title}",
    )
    session.commit()
    return AssistantResponse(
        reply=f"Создал платёж «{payment.title}»: {payment.amount} {payment.currency} ({payment.direction}).",
        intent=IntentName.CREATE_PAYMENT,
        agent=AgentName.FINANCE,
        data={
            "payment_id": str(payment.id),
            "amount": float(payment.amount),
            "direction": payment.direction,
            "status": payment.status,
        },
    )


def _handle_list_payments(session: Session) -> AssistantResponse:
    payments = finance_agent.open_payments(session)
    if not payments:
        return AssistantResponse(
            reply="Открытых платежей нет.",
            intent=IntentName.LIST_PAYMENTS,
            agent=AgentName.FINANCE,
            status="empty",
        )
    lines = [f"• [{item.status}] {item.title}: {item.amount} {item.currency}" for item in payments[:15]]
    return AssistantResponse(
        reply="Открытые платежи:\n" + "\n".join(lines),
        intent=IntentName.LIST_PAYMENTS,
        agent=AgentName.FINANCE,
        data={
            "payments": [
                {
                    "id": str(item.id),
                    "title": item.title,
                    "amount": float(item.amount),
                    "status": item.status,
                    "direction": item.direction,
                }
                for item in payments[:15]
            ]
        },
    )


def _handle_finance_summary(session: Session) -> AssistantResponse:
    summary = finance_agent.summary(session)
    return AssistantResponse(
        reply=(
            "Финансовая сводка (оплаченные):\n"
            f"• Приход: {summary['income_paid']} RUB\n"
            f"• Расход: {summary['expense_paid']} RUB\n"
            f"• Баланс: {summary['balance_paid']} RUB\n"
            f"• Открытых платежей: {summary['open_payments']}"
        ),
        intent=IntentName.FINANCE_SUMMARY,
        agent=AgentName.FINANCE,
        data={key: float(value) if hasattr(value, "as_tuple") else value for key, value in summary.items()},
    )


def _handle_create_event(session: Session, user_id: UUID, payload: AssistantRequest) -> AssistantResponse:
    event = calendar_agent.create_event_from_text(session, payload.message, user_id, payload.project_id)
    log_event(
        session,
        actor_id=user_id,
        entity_type="calendar_event",
        entity_id=event.id,
        action=AuditAction.CREATE,
        summary=f"AI создал событие: {event.title}",
    )
    session.commit()
    return AssistantResponse(
        reply=f"Добавил в календарь: «{event.title}» на {event.starts_at.isoformat()}.",
        intent=IntentName.CREATE_EVENT,
        agent=AgentName.CALENDAR,
        data={
            "event_id": str(event.id),
            "title": event.title,
            "starts_at": event.starts_at.isoformat(),
            "event_type": event.event_type,
        },
    )


def _handle_list_events(session: Session) -> AssistantResponse:
    events = calendar_agent.list_upcoming(session)
    if not events:
        return AssistantResponse(
            reply="Ближайших событий нет.",
            intent=IntentName.LIST_EVENTS,
            agent=AgentName.CALENDAR,
            status="empty",
        )
    lines = [f"• {item.starts_at.date().isoformat()} [{item.event_type}] {item.title}" for item in events[:15]]
    return AssistantResponse(
        reply="Ближайшие события:\n" + "\n".join(lines),
        intent=IntentName.LIST_EVENTS,
        agent=AgentName.CALENDAR,
        data={
            "events": [
                {
                    "id": str(item.id),
                    "title": item.title,
                    "starts_at": item.starts_at.isoformat(),
                    "event_type": item.event_type,
                }
                for item in events[:15]
            ]
        },
    )
