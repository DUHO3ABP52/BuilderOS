from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.events.schemas import AuditEventRead
from app.modules.events.service import list_events

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[AuditEventRead])
def get_events(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[AuditEventRead]:
    return [AuditEventRead.model_validate(event) for event in list_events(session)]
