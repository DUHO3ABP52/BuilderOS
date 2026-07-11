from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.ai.agents.knowledge_agent import search_knowledge_ranked
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.events.models import AuditAction
from app.modules.events.service import log_event
from app.modules.knowledge.indexer import index_item, reindex_all, remove_item
from app.modules.knowledge.models import KnowledgeItem
from app.modules.knowledge.schemas import KnowledgeCreate, KnowledgeRead
from app.services import rag as rag_service

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
    index_item(item)
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


@router.get("/search")
def search_knowledge_endpoint(
    q: str,
    limit: int = 8,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> dict:
    ranked = search_knowledge_ranked(session, q, limit=limit)
    return {
        "query": q,
        "count": len(ranked),
        "items": [
            {
                "id": str(row.item.id),
                "title": row.item.title,
                "category": row.item.category,
                "excerpt": (row.chunk or row.item.content)[:300],
                "score": row.score,
                "source": row.source,
            }
            for row in ranked
        ],
    }


@router.get("/rag-status")
def knowledge_rag_status(_: User = Depends(get_current_user)) -> dict:
    return rag_service.status_payload()


@router.post("/reindex")
def reindex_knowledge(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    result = reindex_all(session)
    log_event(
        session,
        actor_id=user.id,
        entity_type="knowledge",
        entity_id=None,
        action=AuditAction.UPDATE,
        summary="Переиндексация базы знаний в Qdrant",
        payload=result,
    )
    session.commit()
    return {"status": "ok", **result, "rag": rag_service.status_payload()}


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
    remove_item(item.id)
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
