from fastapi.testclient import TestClient


def test_assistant_help(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/api/v1/ai/ask", headers=auth_headers, json={"message": "помощь"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "help"
    assert body["agent"] == "coordinator"


def test_assistant_knowledge_search(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/api/v1/ai/ask", headers=auth_headers, json={"message": "найди ГОСТ"})
    assert response.status_code == 200
    body = response.json()
    assert body["agent"] == "knowledge"
    assert body["intent"] == "search_knowledge"
    assert body["status"] in {"ok", "empty"}


def test_assistant_remember_and_recall(client: TestClient, auth_headers: dict[str, str]) -> None:
    remember = client.post(
        "/api/v1/ai/ask",
        headers=auth_headers,
        json={"message": "запомни: гарантия всегда 24 месяца"},
    )
    assert remember.status_code == 200
    assert remember.json()["agent"] == "memory"

    recall = client.post("/api/v1/ai/ask", headers=auth_headers, json={"message": "что ты помнишь"})
    assert recall.status_code == 200
    assert "24 месяца" in recall.json()["reply"]


def test_assistant_create_task(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/ai/ask",
        headers=auth_headers,
        json={"message": "добавь задачу подписать акт КС-2"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["agent"] == "task"
    assert body["data"]["title"]


def test_assistant_document_needs_data_then_create(client: TestClient, auth_headers: dict[str, str]) -> None:
    missing = client.post("/api/v1/ai/ask", headers=auth_headers, json={"message": "сделай договор"})
    assert missing.status_code == 200
    body = missing.json()
    assert body["agent"] == "document"
    assert body["status"] == "needs_data"
    assert body["missing_fields"]

    created = client.post(
        "/api/v1/ai/ask",
        headers=auth_headers,
        json={
            "message": "сделай договор",
            "variables": {
                "customer": {"name": "ООО Заказчик", "inn": "7707083893"},
                "contractor": {"name": "ИП Подрядчик", "inn": "500100732259"},
                "project": {"name": "ЖК Север", "address": "Москва", "city": "Москва"},
                "contract": {
                    "number": "15/26",
                    "date": "2026-07-11",
                    "price": 2500000,
                    "guarantee_months": 24,
                },
            },
        },
    )
    assert created.status_code == 200, created.text
    result = created.json()
    assert result["status"] == "ok"
    assert result["data"]["document_id"]


def test_llm_status_when_disabled(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/ai/llm-status", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["provider_status"] == "disabled"
    assert body["model_ready"] is False
    assert "warmup" in body
    assert "endpoints" in body
    assert "vision" in body
    assert body["vision"]["enabled"] is False
    assert "teacher" in body
