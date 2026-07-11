from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.knowledge.models import KnowledgeItem


def search_knowledge(session: Session, query: str, limit: int = 10) -> list[KnowledgeItem]:
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
