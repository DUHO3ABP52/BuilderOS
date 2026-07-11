from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.memory.models import MemoryFact
from app.modules.memory.schemas import MemoryCreate


def remember(session: Session, payload: MemoryCreate, user_id: UUID) -> MemoryFact:
    fact = MemoryFact(**payload.model_dump(), created_by_id=user_id)
    session.add(fact)
    session.flush()
    return fact


def recall(session: Session, query: str | None = None, limit: int = 20) -> list[MemoryFact]:
    statement = select(MemoryFact).where(MemoryFact.is_archived.is_(False))
    if query:
        pattern = f"%{query}%"
        statement = statement.where(
            or_(MemoryFact.key.ilike(pattern), MemoryFact.content.ilike(pattern))
        )
    return list(session.scalars(statement.order_by(MemoryFact.created_at.desc()).limit(limit)))
