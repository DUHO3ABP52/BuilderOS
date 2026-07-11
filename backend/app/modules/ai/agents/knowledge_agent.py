from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.knowledge.models import KnowledgeItem
from app.services import rag as rag_service


@dataclass(frozen=True)
class KnowledgeSearchResult:
    item: KnowledgeItem
    score: float | None
    chunk: str | None
    source: str


def search_knowledge_lexical(session: Session, query: str, limit: int = 10) -> list[KnowledgeItem]:
    pattern = f"%{query.strip()}%"
    return list(
        session.scalars(
            select(KnowledgeItem)
            .where(
                KnowledgeItem.is_archived.is_(False),
                or_(KnowledgeItem.title.ilike(pattern), KnowledgeItem.content.ilike(pattern)),
            )
            .order_by(KnowledgeItem.title)
            .limit(limit)
        )
    )


def search_knowledge(session: Session, query: str, limit: int = 10) -> list[KnowledgeItem]:
    ranked = search_knowledge_ranked(session, query, limit=limit)
    return [row.item for row in ranked]


def search_knowledge_ranked(session: Session, query: str, limit: int = 10) -> list[KnowledgeSearchResult]:
    query = query.strip()
    if not query:
        return []

    results: list[KnowledgeSearchResult] = []
    seen: set[UUID] = set()

    if rag_service.rag_is_enabled():
        hits = rag_service.search(query, limit=limit)
        if hits:
            items = {
                item.id: item
                for item in session.scalars(
                    select(KnowledgeItem).where(KnowledgeItem.id.in_([hit.item_id for hit in hits]))
                )
            }
            for hit in hits:
                item = items.get(hit.item_id)
                if item is None or item.is_archived or item.id in seen:
                    continue
                seen.add(item.id)
                results.append(
                    KnowledgeSearchResult(item=item, score=hit.score, chunk=hit.chunk, source="rag")
                )

    if len(results) < limit:
        for item in search_knowledge_lexical(session, query, limit=limit):
            if item.id in seen:
                continue
            seen.add(item.id)
            results.append(KnowledgeSearchResult(item=item, score=None, chunk=None, source="lexical"))
            if len(results) >= limit:
                break

    return results[:limit]
