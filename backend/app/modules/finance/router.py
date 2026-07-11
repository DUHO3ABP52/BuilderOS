from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.events.models import AuditAction
from app.modules.events.service import log_event
from app.modules.finance.models import Payment
from app.modules.finance.schemas import PaymentCreate, PaymentRead, PaymentUpdate
from app.modules.finance.service import create_payment, finance_summary, list_payments, mark_paid, update_payment

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/summary")
def get_finance_summary(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> dict:
    summary = finance_summary(session)
    return {key: float(value) if hasattr(value, "as_tuple") else value for key, value in summary.items()}


@router.post("/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment_endpoint(
    payload: PaymentCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Payment:
    payment = create_payment(session, payload, user.id)
    log_event(
        session,
        actor_id=user.id,
        entity_type="payment",
        entity_id=payment.id,
        action=AuditAction.CREATE,
        summary=f"Создан платёж: {payment.title}",
    )
    session.commit()
    session.refresh(payment)
    return payment


@router.get("/payments", response_model=list[PaymentRead])
def list_payments_endpoint(
    include_paid: bool = True,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[Payment]:
    return list_payments(session, include_paid=include_paid)


@router.patch("/payments/{payment_id}", response_model=PaymentRead)
def update_payment_endpoint(
    payment_id: UUID,
    payload: PaymentUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Payment:
    payment = session.get(Payment, payment_id)
    if payment is None or payment.is_archived:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    update_payment(session, payment, payload)
    log_event(
        session,
        actor_id=user.id,
        entity_type="payment",
        entity_id=payment.id,
        action=AuditAction.UPDATE,
        summary=f"Обновлён платёж: {payment.title}",
    )
    session.commit()
    session.refresh(payment)
    return payment


@router.post("/payments/{payment_id}/paid", response_model=PaymentRead)
def mark_payment_paid(
    payment_id: UUID,
    paid_on: date | None = None,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Payment:
    payment = session.get(Payment, payment_id)
    if payment is None or payment.is_archived:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    mark_paid(session, payment, paid_on=paid_on)
    log_event(
        session,
        actor_id=user.id,
        entity_type="payment",
        entity_id=payment.id,
        action=AuditAction.UPDATE,
        summary=f"Платёж отмечен оплаченным: {payment.title}",
    )
    session.commit()
    session.refresh(payment)
    return payment


@router.post("/payments/{payment_id}/archive", response_model=PaymentRead)
def archive_payment(
    payment_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Payment:
    payment = session.get(Payment, payment_id)
    if payment is None or payment.is_archived:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    payment.is_archived = True
    log_event(
        session,
        actor_id=user.id,
        entity_type="payment",
        entity_id=payment.id,
        action=AuditAction.ARCHIVE,
        summary=f"Архивирован платёж: {payment.title}",
    )
    session.commit()
    session.refresh(payment)
    return payment
