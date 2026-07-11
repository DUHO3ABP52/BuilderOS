from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.tasks.schemas import TaskCreate
from app.modules.tasks.service import create_task, list_tasks


def create_task_from_text(
    session: Session,
    title: str,
    user_id: UUID,
    project_id: UUID | None = None,
    description: str | None = None,
):
    return create_task(
        session,
        TaskCreate(title=title.strip()[:255], description=description, project_id=project_id),
        user_id,
    )


def open_tasks(session: Session):
    return list_tasks(session, include_done=False)
