from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


def test_finance_payment_flow(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = client.post(
        "/api/v1/finance/payments",
        headers=auth_headers,
        json={
            "title": "Аванс по договору 15/26",
            "direction": "income",
            "kind": "advance",
            "amount": 150000,
        },
    )
    assert created.status_code == 201, created.text
    payment_id = created.json()["id"]

    listed = client.get("/api/v1/finance/payments", headers=auth_headers)
    assert listed.status_code == 200
    assert any(item["id"] == payment_id for item in listed.json())

    paid = client.post(f"/api/v1/finance/payments/{payment_id}/paid", headers=auth_headers)
    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"

    summary = client.get("/api/v1/finance/summary", headers=auth_headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["income_paid"] >= 150000
    assert "balance_paid" in body


def test_calendar_event_flow(client: TestClient, auth_headers: dict[str, str]) -> None:
    starts = datetime.now(timezone.utc) + timedelta(days=2)
    created = client.post(
        "/api/v1/calendar/events",
        headers=auth_headers,
        json={
            "title": "Выезд на объект ЖК Север",
            "event_type": "site_visit",
            "starts_at": starts.isoformat(),
            "ends_at": (starts + timedelta(hours=2)).isoformat(),
            "location": "Москва",
        },
    )
    assert created.status_code == 201, created.text
    event_id = created.json()["id"]

    upcoming = client.get("/api/v1/calendar/upcoming?days=14", headers=auth_headers)
    assert upcoming.status_code == 200
    assert any(item["id"] == event_id for item in upcoming.json())

    archived = client.post(f"/api/v1/calendar/events/{event_id}/archive", headers=auth_headers)
    assert archived.status_code == 200
    assert archived.json()["is_archived"] is True


def test_assistant_finance_and_calendar(client: TestClient, auth_headers: dict[str, str]) -> None:
    payment = client.post(
        "/api/v1/ai/ask",
        headers=auth_headers,
        json={"message": "добавь платёж аванс 75000"},
    )
    assert payment.status_code == 200
    assert payment.json()["agent"] == "finance"
    assert payment.json()["intent"] == "create_payment"
    assert payment.json()["data"]["amount"] == 75000.0

    summary = client.post("/api/v1/ai/ask", headers=auth_headers, json={"message": "баланс"})
    assert summary.status_code == 200
    assert summary.json()["intent"] == "finance_summary"

    event = client.post(
        "/api/v1/ai/ask",
        headers=auth_headers,
        json={"message": "добавь встречу завтра с заказчиком"},
    )
    assert event.status_code == 200
    assert event.json()["agent"] == "calendar"
    assert event.json()["intent"] == "create_event"

    listed = client.post("/api/v1/ai/ask", headers=auth_headers, json={"message": "что в календаре"})
    assert listed.status_code == 200
    assert listed.json()["intent"] == "list_events"


def test_dashboard_includes_finance_calendar(client: TestClient, auth_headers: dict[str, str]) -> None:
    dashboard = client.get("/api/v1/dashboard", headers=auth_headers)
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert "payments_open" in body["counts"]
    assert "events_week" in body["counts"]
    assert "finance" in body
    assert "upcoming_events" in body
