from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.tasks.models import Task, TaskStatus
from app.modules.tasks.schemas import TaskCreate, TaskUpdate


def create_task(session: Session, payload: TaskCreate, user_id: UUID) -> Task:
    task = Task(**payload.model_dump(), created_by_id=user_id)
    session.add(task)
    session.flush()
    return task


def list_tasks(session: Session, *, include_done: bool = False) -> list[Task]:
    query = select(Task).where(Task.is_archived.is_(False))
    if not include_done:
        query = query.where(Task.status.in_([TaskStatus.OPEN.value, TaskStatus.IN_PROGRESS.value]))
    return list(session.scalars(query.order_by(Task.created_at.desc())))


def update_task(session: Session, task: Task, payload: TaskUpdate) -> Task:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value.value if hasattr(value, "value") else value)
    session.flush()
    return task
