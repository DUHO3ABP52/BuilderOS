from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.events.models import AuditAction, AuditEvent


def log_event(
    session: Session,
    *,
    actor_id: UUID | None,
    entity_type: str,
    entity_id: UUID | None,
    action: AuditAction,
    summary: str,
    payload: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action.value,
        summary=summary,
        payload=payload,
    )
    session.add(event)
    session.flush()
    return event


def list_events(session: Session, limit: int = 100) -> list[AuditEvent]:
    return list(session.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)))
