from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.calendar.models import CalendarEventType
from app.modules.calendar.schemas import CalendarEventCreate
from app.modules.calendar.service import create_event, upcoming_events


def _parse_when(message: str) -> datetime:
    now = datetime.now(timezone.utc)
    text = message.lower()
    if "послезавтра" in text:
        return (now + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
    if "завтра" in text:
        return (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    if "сегодня" in text:
        return now.replace(hour=15, minute=0, second=0, microsecond=0)
    match = re.search(r"\b(\d{2})\.(\d{2})\.(\d{4})\b", message)
    if match:
        day, month, year = map(int, match.groups())
        return datetime(year, month, day, 10, 0, tzinfo=timezone.utc)
    return (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)


def _detect_type(message: str) -> CalendarEventType:
    text = message.lower()
    if "встреч" in text or "созвон" in text:
        return CalendarEventType.MEETING
    if "выезд" in text or "объект" in text:
        return CalendarEventType.SITE_VISIT
    if "оплат" in text or "платёж" in text or "платеж" in text:
        return CalendarEventType.PAYMENT
    if "срок" in text or "дедлайн" in text:
        return CalendarEventType.DEADLINE
    if "документ" in text or "подпис" in text:
        return CalendarEventType.DOCUMENT
    return CalendarEventType.OTHER


def create_event_from_text(session: Session, message: str, user_id: UUID, project_id: UUID | None = None):
    starts_at = _parse_when(message)
    title = re.sub(
        r"(добавь|создай|поставь)?\s*(событие|встречу|в календарь)?\s*",
        "",
        message,
        flags=re.IGNORECASE,
    ).strip() or "Событие BuilderOS"
    event_type = _detect_type(message)
    return create_event(
        session,
        CalendarEventCreate(
            title=title[:255],
            event_type=event_type,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            project_id=project_id,
            description=f"Создано AI из запроса: {message}",
        ),
        user_id,
    )


def list_upcoming(session: Session, days: int = 14):
    return upcoming_events(session, days=days)
