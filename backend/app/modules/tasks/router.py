from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.events.models import AuditAction
from app.modules.events.service import log_event
from app.modules.tasks.models import Task
from app.modules.tasks.schemas import TaskCreate, TaskRead, TaskUpdate
from app.modules.tasks.service import create_task, list_tasks, update_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task_endpoint(
    payload: TaskCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Task:
    task = create_task(session, payload, user.id)
    log_event(
        session,
        actor_id=user.id,
        entity_type="task",
        entity_id=task.id,
        action=AuditAction.CREATE,
        summary=f"Создана задача: {task.title}",
    )
    session.commit()
    session.refresh(task)
    return task


@router.get("", response_model=list[TaskRead])
def list_tasks_endpoint(
    include_done: bool = False,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[Task]:
    return list_tasks(session, include_done=include_done)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task_endpoint(
    task_id: UUID,
    payload: TaskUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Task:
    task = session.get(Task, task_id)
    if task is None or task.is_archived:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    update_task(session, task, payload)
    log_event(
        session,
        actor_id=user.id,
        entity_type="task",
        entity_id=task.id,
        action=AuditAction.UPDATE,
        summary=f"Обновлена задача: {task.title}",
    )
    session.commit()
    session.refresh(task)
    return task


@router.post("/{task_id}/archive", response_model=TaskRead)
def archive_task(
    task_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Task:
    task = session.get(Task, task_id)
    if task is None or task.is_archived:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    task.is_archived = True
    log_event(
        session,
        actor_id=user.id,
        entity_type="task",
        entity_id=task.id,
        action=AuditAction.ARCHIVE,
        summary=f"Архивирована задача: {task.title}",
    )
    session.commit()
    session.refresh(task)
    return task
