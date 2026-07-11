from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.ai.coordinator import handle_assistant
from app.modules.ai.schemas import AssistantRequest, AssistantResponse
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.events.models import AuditAction
from app.modules.events.service import log_event
from app.services import llm as llm_service
from app.services.llm import LLMError
from app.services.teacher import learn_from_teacher, sanitize_for_teacher

router = APIRouter(prefix="/ai", tags=["ai"])


class TeacherAskRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    project_id: UUID | None = None
    save: bool = False


@router.post("/ask", response_model=AssistantResponse)
def ask_assistant(
    payload: AssistantRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> AssistantResponse:
    return handle_assistant(session, user.id, payload)


@router.get("/llm-status")
def llm_status(_: User = Depends(get_current_user)) -> dict:
    return llm_service.status_payload()


@router.post("/teacher/preview")
def teacher_preview(payload: TeacherAskRequest, _: User = Depends(get_current_user)) -> dict:
    sanitized, redactions = sanitize_for_teacher(payload.message)
    return {"sanitized_question": sanitized, "redactions": redactions}


@router.post("/teacher/ask")
def teacher_ask(
    payload: TeacherAskRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        result = learn_from_teacher(
            session,
            question=payload.message,
            user_id=user.id,
            project_id=payload.project_id,
            save=payload.save,
        )
    except (ValueError, LLMError) as error:
        return {"status": "error", "detail": str(error)}

    if result.saved and result.memory_id:
        log_event(
            session,
            actor_id=user.id,
            entity_type="memory",
            entity_id=result.memory_id,
            action=AuditAction.CREATE,
            summary="Сохранён PATTERN от учителя",
        )
        session.commit()
    else:
        session.rollback()

    return {
        "status": "ok" if result.saved else "needs_confirmation",
        "sanitized_question": result.sanitized_question,
        "redactions": result.redactions,
        "answer": result.answer,
        "saved": result.saved,
        "memory_id": str(result.memory_id) if result.memory_id else None,
    }
