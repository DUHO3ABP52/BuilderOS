from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.events.models import AuditAction
from app.modules.events.service import log_event
from app.modules.knowledge.models import KnowledgeItem
from app.modules.knowledge.schemas import KnowledgeCreate, KnowledgeRead

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("", response_model=KnowledgeRead, status_code=status.HTTP_201_CREATED)
def create_knowledge_item(
    payload: KnowledgeCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> KnowledgeItem:
    item = KnowledgeItem(**payload.model_dump())
    session.add(item)
    session.flush()
    log_event(
        session,
        actor_id=user.id,
        entity_type="knowledge",
        entity_id=item.id,
        action=AuditAction.CREATE,
        summary=f"Добавлена запись базы знаний: {item.title}",
    )
    session.commit()
    session.refresh(item)
    return item


@router.get("", response_model=list[KnowledgeRead])
def list_knowledge_items(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[KnowledgeItem]:
    return list(
        session.scalars(
            select(KnowledgeItem).where(KnowledgeItem.is_archived.is_(False)).order_by(KnowledgeItem.title)
        )
    )


@router.get("/{item_id}", response_model=KnowledgeRead)
def get_knowledge_item(
    item_id: UUID,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> KnowledgeItem:
    item = session.get(KnowledgeItem, item_id)
    if item is None or item.is_archived:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return item


@router.post("/{item_id}/archive", response_model=KnowledgeRead)
def archive_knowledge_item(
    item_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> KnowledgeItem:
    item = session.get(KnowledgeItem, item_id)
    if item is None or item.is_archived:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    item.is_archived = True
    log_event(
        session,
        actor_id=user.id,
        entity_type="knowledge",
        entity_id=item.id,
        action=AuditAction.ARCHIVE,
        summary=f"Архивирована запись: {item.title}",
    )
    session.commit()
    session.refresh(item)
    return item
