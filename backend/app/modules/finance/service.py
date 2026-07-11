from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.finance.models import Payment, PaymentDirection, PaymentStatus
from app.modules.finance.schemas import PaymentCreate, PaymentUpdate


def create_payment(session: Session, payload: PaymentCreate, user_id: UUID) -> Payment:
    payment = Payment(**payload.model_dump(), created_by_id=user_id)
    session.add(payment)
    session.flush()
    return payment


def list_payments(session: Session, *, include_paid: bool = True) -> list[Payment]:
    query = select(Payment).where(Payment.is_archived.is_(False))
    if not include_paid:
        query = query.where(Payment.status.in_([PaymentStatus.PLANNED.value, PaymentStatus.DUE.value, PaymentStatus.OVERDUE.value]))
    return list(session.scalars(query.order_by(Payment.due_on.asc().nulls_last(), Payment.created_at.desc())))


def update_payment(session: Session, payment: Payment, payload: PaymentUpdate) -> Payment:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(payment, field, value.value if hasattr(value, "value") else value)
    session.flush()
    return payment


def mark_paid(session: Session, payment: Payment, paid_on: date | None = None) -> Payment:
    payment.status = PaymentStatus.PAID.value
    payment.paid_on = paid_on or date.today()
    session.flush()
    return payment


def finance_summary(session: Session) -> dict[str, Decimal | int]:
    income = session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.is_archived.is_(False),
            Payment.direction == PaymentDirection.INCOME.value,
            Payment.status == PaymentStatus.PAID.value,
        )
    ) or Decimal("0")
    expense = session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.is_archived.is_(False),
            Payment.direction == PaymentDirection.EXPENSE.value,
            Payment.status == PaymentStatus.PAID.value,
        )
    ) or Decimal("0")
    planned = session.scalar(
        select(func.count()).select_from(Payment).where(
            Payment.is_archived.is_(False),
            Payment.status.in_([PaymentStatus.PLANNED.value, PaymentStatus.DUE.value, PaymentStatus.OVERDUE.value]),
        )
    ) or 0
    return {
        "income_paid": Decimal(income),
        "expense_paid": Decimal(expense),
        "balance_paid": Decimal(income) - Decimal(expense),
        "open_payments": int(planned),
    }
