from __future__ import annotations

import re
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.finance.models import PaymentDirection, PaymentKind, PaymentStatus
from app.modules.finance.schemas import PaymentCreate
from app.modules.finance.service import create_payment, finance_summary, list_payments


def _extract_amount(text: str) -> Decimal | None:
    normalized = text.replace("\u00a0", " ")
    match = re.search(r"(\d{1,3}(?:[ ]\d{3})+(?:[.,]\d{2})?)", normalized)
    if not match:
        match = re.search(r"(\d+(?:[.,]\d{2})?)", normalized)
    if not match:
        return None
    raw = match.group(1).replace(" ", "").replace(",", ".")
    try:
        value = Decimal(raw)
    except Exception:
        return None
    return value if value > 0 else None


def _detect_direction(text: str) -> PaymentDirection:
    lowered = text.lower()
    if any(token in lowered for token in ["расход", "оплатить постав", "купить", "зарплат", "материал"]):
        return PaymentDirection.EXPENSE
    return PaymentDirection.INCOME


def _detect_kind(text: str) -> PaymentKind:
    lowered = text.lower()
    if "аванс" in lowered:
        return PaymentKind.ADVANCE
    if "кс" in lowered or "акт" in lowered:
        return PaymentKind.ACT
    if "счет" in lowered or "счёт" in lowered:
        return PaymentKind.INVOICE
    if "материал" in lowered:
        return PaymentKind.MATERIAL
    if "зарплат" in lowered:
        return PaymentKind.SALARY
    return PaymentKind.OTHER


def create_payment_from_text(session: Session, message: str, user_id: UUID, project_id: UUID | None = None):
    amount = _extract_amount(message)
    if amount is None:
        raise ValueError("Не нашёл сумму платежа. Пример: «добавь платёж аванс 150000»")
    title_match = re.sub(
        r"(добавь|создай|запиши)?\s*(платёж|платеж|оплату|оплата)?\s*",
        "",
        message,
        flags=re.IGNORECASE,
    ).strip()
    title = title_match[:255] if title_match else f"Платёж {amount}"
    direction = _detect_direction(message)
    kind = _detect_kind(message)
    due = date.today() + timedelta(days=7)
    return create_payment(
        session,
        PaymentCreate(
            title=title,
            direction=direction,
            kind=kind,
            status=PaymentStatus.PLANNED,
            amount=amount,
            project_id=project_id,
            due_on=due,
            description=f"Создано AI из запроса: {message}",
        ),
        user_id,
    )


def open_payments(session: Session):
    return list_payments(session, include_paid=False)


def summary(session: Session):
    return finance_summary(session)
