from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.memory.models import MemoryKind
from app.modules.memory.schemas import MemoryCreate
from app.modules.memory.service import recall, remember


def remember_text(session: Session, text: str, user_id: UUID, project_id: UUID | None = None):
    key = text[:80].strip().lower().replace(" ", "-") or "fact"
    return remember(
        session,
        MemoryCreate(
            kind=MemoryKind.FACT,
            key=key,
            content=text.strip(),
            source="assistant",
            project_id=project_id,
        ),
        user_id,
    )


def recall_text(session: Session, query: str | None = None):
    return recall(session, query=query)
