from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.calendar.models import CalendarEvent
from app.modules.calendar.schemas import CalendarEventCreate, CalendarEventRead, CalendarEventUpdate
from app.modules.calendar.service import create_event, list_events, upcoming_events, update_event
from app.modules.events.models import AuditAction
from app.modules.events.service import log_event

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.post("/events", response_model=CalendarEventRead, status_code=status.HTTP_201_CREATED)
def create_calendar_event(
    payload: CalendarEventCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CalendarEvent:
    event = create_event(session, payload, user.id)
    log_event(
        session,
        actor_id=user.id,
        entity_type="calendar_event",
        entity_id=event.id,
        action=AuditAction.CREATE,
        summary=f"Создано событие: {event.title}",
    )
    session.commit()
    session.refresh(event)
    return event


@router.get("/events", response_model=list[CalendarEventRead])
def list_calendar_events(
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[CalendarEvent]:
    return list_events(session, from_dt=from_dt, to_dt=to_dt)


@router.get("/upcoming", response_model=list[CalendarEventRead])
def list_upcoming_events(
    days: int = 14,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[CalendarEvent]:
    return upcoming_events(session, days=days)


@router.patch("/events/{event_id}", response_model=CalendarEventRead)
def update_calendar_event(
    event_id: UUID,
    payload: CalendarEventUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CalendarEvent:
    event = session.get(CalendarEvent, event_id)
    if event is None or event.is_archived:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    try:
        update_event(session, event, payload)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    log_event(
        session,
        actor_id=user.id,
        entity_type="calendar_event",
        entity_id=event.id,
        action=AuditAction.UPDATE,
        summary=f"Обновлено событие: {event.title}",
    )
    session.commit()
    session.refresh(event)
    return event


@router.post("/events/{event_id}/archive", response_model=CalendarEventRead)
def archive_calendar_event(
    event_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CalendarEvent:
    event = session.get(CalendarEvent, event_id)
    if event is None or event.is_archived:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    event.is_archived = True
    log_event(
        session,
        actor_id=user.id,
        entity_type="calendar_event",
        entity_id=event.id,
        action=AuditAction.ARCHIVE,
        summary=f"Архивировано событие: {event.title}",
    )
    session.commit()
    session.refresh(event)
    return event
