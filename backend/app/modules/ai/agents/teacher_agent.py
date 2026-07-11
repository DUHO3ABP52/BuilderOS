from uuid import UUID

from sqlalchemy.orm import Session

from app.services.teacher import TeacherResult, learn_from_teacher, sanitize_for_teacher


def preview_sanitize(message: str) -> tuple[str, list[str]]:
    return sanitize_for_teacher(message)


def ask(
    session: Session,
    message: str,
    user_id: UUID,
    *,
    project_id: UUID | None = None,
    save: bool = False,
) -> TeacherResult:
    return learn_from_teacher(
        session,
        question=message,
        user_id=user_id,
        project_id=project_id,
        save=save,
    )
