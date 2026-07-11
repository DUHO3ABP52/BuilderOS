from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.ai.coordinator import handle_assistant
from app.modules.ai.schemas import AssistantRequest, AssistantResponse
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/ask", response_model=AssistantResponse)
def ask_assistant(
    payload: AssistantRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> AssistantResponse:
    return handle_assistant(session, user.id, payload)
