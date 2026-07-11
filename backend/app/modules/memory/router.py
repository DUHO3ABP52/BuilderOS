from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.events.models import AuditAction
from app.modules.events.service import log_event
from app.modules.memory.models import MemoryFact
from app.modules.memory.schemas import MemoryCreate, MemoryRead
from app.modules.memory.service import recall, remember

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
def create_memory(
    payload: MemoryCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> MemoryFact:
    fact = remember(session, payload, user.id)
    log_event(
        session,
        actor_id=user.id,
        entity_type="memory",
        entity_id=fact.id,
        action=AuditAction.CREATE,
        summary=f"Сохранена память: {fact.key}",
    )
    session.commit()
    session.refresh(fact)
    return fact


@router.get("", response_model=list[MemoryRead])
def list_memory(
    q: str | None = None,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[MemoryFact]:
    return recall(session, query=q)


@router.post("/{fact_id}/archive", response_model=MemoryRead)
def archive_memory(
    fact_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> MemoryFact:
    fact = session.get(MemoryFact, fact_id)
    if fact is None or fact.is_archived:
        raise HTTPException(status_code=404, detail="Запись памяти не найдена")
    fact.is_archived = True
    log_event(
        session,
        actor_id=user.id,
        entity_type="memory",
        entity_id=fact.id,
        action=AuditAction.ARCHIVE,
        summary=f"Архивирована память: {fact.key}",
    )
    session.commit()
    session.refresh(fact)
    return fact
