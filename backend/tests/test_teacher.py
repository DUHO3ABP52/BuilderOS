from unittest.mock import patch

from app.services.teacher import sanitize_for_teacher
from fastapi.testclient import TestClient


def test_sanitize_for_teacher_redacts_pii() -> None:
    text = (
        "Спроси учителя: как обычно пишут гарантию в договоре с ООО Ромашка "
        "ИНН 7707083893 на сумму 1 500 000 руб по адресу, email test@example.com"
    )
    sanitized, redactions = sanitize_for_teacher(text)
    assert "7707083893" not in sanitized
    assert "1 500 000" not in sanitized
    assert "test@example.com" not in sanitized
    assert "inn_10" in redactions or "inn_12" in redactions
    assert "amount" in redactions
    assert "email" in redactions
    assert "company" in redactions


def test_assistant_ask_teacher_needs_confirmation(client: TestClient, auth_headers: dict[str, str], monkeypatch) -> None:
    monkeypatch.setattr("app.core.config.settings.llm_enabled", True)
    monkeypatch.setattr("app.core.config.settings.llm_teacher_enabled", True)
    monkeypatch.setattr("app.core.config.settings.llm_cloud_for_teacher", True)
    monkeypatch.setattr("app.core.config.settings.llm_teacher_auto_save", False)

    with (
        patch("app.services.llm.llm_is_configured", return_value=True),
        patch(
            "app.services.llm.chat_teacher",
            return_value="1) Обычно 24 месяца.\n2) Типовая формулировка...\n3) Проверьте локально.",
        ),
    ):
        response = client.post(
            "/api/v1/ai/ask",
            headers=auth_headers,
            json={"message": "спроси учителя: как обычно формулируют гарантийный срок"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["agent"] == "teacher"
    assert body["intent"] == "ask_teacher"
    assert body["status"] == "needs_confirmation"
    assert body["data"]["saved"] is False
    assert "гарантий" in body["data"]["answer"].lower() or "24" in body["data"]["answer"]


def test_assistant_ask_teacher_saves_pattern(client: TestClient, auth_headers: dict[str, str], monkeypatch) -> None:
    monkeypatch.setattr("app.core.config.settings.llm_enabled", True)
    monkeypatch.setattr("app.core.config.settings.llm_teacher_enabled", True)
    monkeypatch.setattr("app.core.config.settings.llm_cloud_for_teacher", True)

    with (
        patch("app.services.llm.llm_is_configured", return_value=True),
        patch(
            "app.services.llm.chat_teacher",
            return_value="Типовой паттерн: гарантия 24 месяца с момента сдачи.",
        ),
    ):
        response = client.post(
            "/api/v1/ai/ask",
            headers=auth_headers,
            json={
                "message": "спроси учителя: как обычно формулируют гарантию",
                "confirm": True,
            },
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"
    assert body["data"]["saved"] is True
    assert body["data"]["memory_id"]

    memory = client.get("/api/v1/memory", headers=auth_headers, params={"q": "teacher:"})
    assert memory.status_code == 200
    assert any(item["source"] == "teacher" for item in memory.json())


def test_teacher_preview_endpoint(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/ai/teacher/preview",
        headers=auth_headers,
        json={"message": "Вопрос про ООО Тест ИНН 500100732259"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "500100732259" not in body["sanitized_question"]
    assert body["redactions"]
