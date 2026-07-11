from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.calendar.service import upcoming_events
from app.modules.companies.models import Company
from app.modules.documents.models import Document
from app.modules.events.service import list_events
from app.modules.finance.models import Payment, PaymentStatus
from app.modules.finance.service import finance_summary
from app.modules.knowledge.models import KnowledgeItem
from app.modules.projects.models import Project
from app.modules.tasks.models import Task, TaskStatus
from app.modules.templates.models import DocumentTemplate

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    summary = finance_summary(session)
    upcoming = upcoming_events(session, days=7, limit=5)
    return {
        "counts": {
            "companies": session.scalar(select(func.count()).select_from(Company).where(Company.is_archived.is_(False))) or 0,
            "projects": session.scalar(select(func.count()).select_from(Project).where(Project.is_archived.is_(False))) or 0,
            "documents": session.scalar(select(func.count()).select_from(Document).where(Document.is_archived.is_(False))) or 0,
            "templates": session.scalar(
                select(func.count()).select_from(DocumentTemplate).where(DocumentTemplate.is_archived.is_(False))
            )
            or 0,
            "knowledge": session.scalar(
                select(func.count()).select_from(KnowledgeItem).where(KnowledgeItem.is_archived.is_(False))
            )
            or 0,
            "tasks": session.scalar(
                select(func.count())
                .select_from(Task)
                .where(Task.is_archived.is_(False), Task.status.in_([TaskStatus.OPEN.value, TaskStatus.IN_PROGRESS.value]))
            )
            or 0,
            "payments_open": session.scalar(
                select(func.count())
                .select_from(Payment)
                .where(
                    Payment.is_archived.is_(False),
                    Payment.status.in_([PaymentStatus.PLANNED.value, PaymentStatus.DUE.value, PaymentStatus.OVERDUE.value]),
                )
            )
            or 0,
            "events_week": len(upcoming),
        },
        "finance": {key: float(value) if hasattr(value, "as_tuple") else value for key, value in summary.items()},
        "upcoming_events": [
            {
                "id": str(event.id),
                "title": event.title,
                "event_type": event.event_type,
                "starts_at": event.starts_at.isoformat(),
            }
            for event in upcoming
        ],
        "recent_events": [
            {
                "id": str(event.id),
                "summary": event.summary,
                "action": event.action,
                "entity_type": event.entity_type,
                "created_at": event.created_at.isoformat(),
            }
            for event in list_events(session, limit=10)
        ],
    }
