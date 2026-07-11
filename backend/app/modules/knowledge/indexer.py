from __future__ import annotations

import logging
import threading
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.knowledge.models import KnowledgeItem
from app.services import rag as rag_service

logger = logging.getLogger(__name__)
_reindex_lock = threading.Lock()
_reindex_started = False


def index_item(item: KnowledgeItem) -> int:
    if item.is_archived:
        rag_service.delete_knowledge_item(item.id)
        return 0
    return rag_service.upsert_knowledge_item(
        item_id=item.id,
        title=item.title,
        category=item.category,
        content=item.content,
    )


def remove_item(item_id: UUID) -> None:
    rag_service.delete_knowledge_item(item_id)


def reindex_all(session: Session) -> dict[str, int]:
    items = list(session.scalars(select(KnowledgeItem).where(KnowledgeItem.is_archived.is_(False))))
    payload = [
        {
            "id": item.id,
            "title": item.title,
            "category": item.category,
            "content": item.content,
        }
        for item in items
    ]
    return rag_service.reindex_items(payload)


def start_reindex_background(session_factory) -> None:
    """Фоновая индексация после старта API."""
    global _reindex_started
    if not rag_service.rag_is_enabled():
        return
    with _reindex_lock:
        if _reindex_started:
            return
        _reindex_started = True

    def _run() -> None:
        rag_service.warmup_embedding_model()
        session = session_factory()
        try:
            result = reindex_all(session)
            logger.info("RAG reindex complete: %s", result)
        except Exception as exc:
            logger.warning("RAG reindex failed: %s", exc)
        finally:
            session.close()

    threading.Thread(target=_run, name="rag-reindex", daemon=True).start()
