from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.ai.agents import document_agent, knowledge_agent, memory_agent, task_agent
from app.modules.ai.schemas import AgentName, AssistantAction, AssistantRequest, AssistantResponse, IntentName
from app.modules.events.models import AuditAction
from app.modules.events.service import log_event


def classify_intent(message: str) -> IntentName:
    text = message.lower().strip()
    if any(token in text for token in ["помощь", "что умеешь", "help", "команды"]):
        return IntentName.HELP
    if any(token in text for token in ["запомни", "запомнить", "учти что"]):
        return IntentName.REMEMBER
    if any(token in text for token in ["что ты помнишь", "вспомни", "память"]):
        return IntentName.RECALL
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


def _extract_after(message: str, markers: list[str]) -> str:
    lower = message.lower()
    for marker in markers:
        index = lower.find(marker)
        if index >= 0:
            return message[index + len(marker) :].strip(" :,-")
    return message.strip()


def handle_assistant(session: Session, user_id: UUID, payload: AssistantRequest) -> AssistantResponse:
    intent = classify_intent(payload.message)
    if intent == IntentName.HELP:
        return AssistantResponse(
            reply=(
                "Я координатор BuilderOS. Могу:\n"
                "• подготовить документ из шаблона («сделай договор»)\n"
                "• искать по базе знаний («найди СП»)\n"
                "• создавать задачи («добавь задачу подписать акт»)\n"
                "• запоминать факты («запомни: гарантия всегда 24 месяца»)"
            ),
            intent=intent,
            agent=AgentName.COORDINATOR,
        )

    if intent == IntentName.CREATE_DOCUMENT:
        return _handle_document(session, user_id, payload)
    if intent == IntentName.SEARCH_KNOWLEDGE:
        return _handle_knowledge(session, user_id, payload)
    if intent == IntentName.REMEMBER:
        return _handle_remember(session, user_id, payload)
    if intent == IntentName.RECALL:
        return _handle_recall(session, payload)
    if intent == IntentName.CREATE_TASK:
        return _handle_create_task(session, user_id, payload)
    if intent == IntentName.LIST_TASKS:
        return _handle_list_tasks(session)

    return AssistantResponse(
        reply=(
            "Не уверен, что сделать. Попробуйте: «сделай договор», «найди ГОСТ», "
            "«добавь задачу…» или «запомни…». Напишите «помощь» для списка команд."
        ),
        intent=IntentName.UNKNOWN,
        agent=AgentName.COORDINATOR,
        status="needs_clarification",
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
    if missing and not payload.confirm:
        labels = ", ".join(missing)
        return AssistantResponse(
            reply=(
                f"Нашёл шаблон «{template.name}» (v{template.version}). "
                f"Не хватает данных: {labels}. Передайте variables и повторите запрос "
                "или подтвердите создание черновика с частичными данными (confirm=true)."
            ),
            intent=IntentName.CREATE_DOCUMENT,
            agent=AgentName.DOCUMENT,
            status="needs_data",
            missing_fields=missing,
            data={"template_id": str(template.id), "template_name": template.name},
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
        ),
        intent=IntentName.CREATE_DOCUMENT,
        agent=AgentName.DOCUMENT,
        data={
            "document_id": str(document.id),
            "template_id": str(template.id),
            "current_version": document.current_version,
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


def _handle_knowledge(session: Session, user_id: UUID, payload: AssistantRequest) -> AssistantResponse:
    query = _extract_after(payload.message, ["найди", "поиск", "что говорит", "база знаний"])
    query = re.sub(r"^(в\s+)?(базе\s+знаний|сп|снип|гост)\s*", "", query, flags=re.IGNORECASE).strip() or payload.message
    items = knowledge_agent.search_knowledge(session, query)
    log_event(
        session,
        actor_id=user_id,
        entity_type="knowledge",
        entity_id=None,
        action=AuditAction.UPDATE,
        summary=f"AI поиск по знаниям: {query[:120]}",
        payload={"agent": "knowledge", "found": len(items)},
    )
    session.commit()
    if not items:
        return AssistantResponse(
            reply=f"По запросу «{query}» в базе знаний ничего не нашёл. Добавьте СП/ГОСТ в раздел знаний.",
            intent=IntentName.SEARCH_KNOWLEDGE,
            agent=AgentName.KNOWLEDGE,
            status="empty",
            data={"query": query},
        )
    lines = [f"• {item.title} [{item.category}]" for item in items[:8]]
    return AssistantResponse(
        reply="Нашёл в базе знаний:\n" + "\n".join(lines),
        intent=IntentName.SEARCH_KNOWLEDGE,
        agent=AgentName.KNOWLEDGE,
        data={
            "query": query,
            "items": [
                {"id": str(item.id), "title": item.title, "category": item.category, "excerpt": item.content[:240]}
                for item in items[:8]
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
    facts = memory_agent.recall_text(session, query if query and query != payload.message else None)
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
