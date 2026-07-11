from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.calendar.models import CalendarEvent
from app.modules.calendar.schemas import CalendarEventCreate, CalendarEventUpdate


def create_event(session: Session, payload: CalendarEventCreate, user_id: UUID) -> CalendarEvent:
    event = CalendarEvent(**payload.model_dump(), created_by_id=user_id)
    session.add(event)
    session.flush()
    return event


def list_events(
    session: Session,
    *,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
) -> list[CalendarEvent]:
    query = select(CalendarEvent).where(CalendarEvent.is_archived.is_(False))
    if from_dt is not None:
        query = query.where(CalendarEvent.starts_at >= from_dt)
    if to_dt is not None:
        query = query.where(CalendarEvent.starts_at <= to_dt)
    return list(session.scalars(query.order_by(CalendarEvent.starts_at.asc())))


def upcoming_events(session: Session, *, days: int = 14, limit: int = 20) -> list[CalendarEvent]:
    now = datetime.now(timezone.utc)
    until = now + timedelta(days=days)
    return list_events(session, from_dt=now, to_dt=until)[:limit]


def update_event(session: Session, event: CalendarEvent, payload: CalendarEventUpdate) -> CalendarEvent:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(event, field, value.value if hasattr(value, "value") else value)
    if event.ends_at and event.starts_at and event.ends_at < event.starts_at:
        raise ValueError("Дата окончания не может быть раньше начала")
    session.flush()
    return event
