from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["project"] == "BuilderOS"


def test_login_and_me(client: TestClient, auth_headers: dict[str, str]) -> None:
    me = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me.status_code == 200
    assert me.json()["email"] == "admin@example.com"


def test_company_project_document_flow(client: TestClient, auth_headers: dict[str, str]) -> None:
    company = client.post(
        "/api/v1/companies",
        headers=auth_headers,
        json={"name": "ООО Заказчик", "kind": "customer", "inn": "7707083893"},
    )
    assert company.status_code == 201, company.text

    project = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"name": "ЖК Север", "address": "Москва", "customer_id": company.json()["id"]},
    )
    assert project.status_code == 201, project.text

    templates = client.get("/api/v1/templates", headers=auth_headers)
    assert templates.status_code == 200
    assert len(templates.json()) >= 1
    template_id = templates.json()[0]["id"]

    document = client.post(
        f"/api/v1/documents/from-template/{template_id}",
        headers=auth_headers,
        json={
            "project_id": project.json()["id"],
            "title": "Договор на фасад",
            "variables": {
                "customer": {"name": "ООО Заказчик", "inn": "7707083893"},
                "contractor": {"name": "ИП Подрядчик", "inn": "500100732259"},
                "project": {"name": "ЖК Север", "address": "Москва", "city": "Москва"},
                "contract": {
                    "number": "12/26",
                    "date": "2026-07-11",
                    "price": 1500000,
                    "guarantee_months": 24,
                },
            },
        },
    )
    assert document.status_code == 201, document.text
    document_id = document.json()["id"]

    docx = client.get(f"/api/v1/documents/{document_id}/export/docx", headers=auth_headers)
    assert docx.status_code == 200

    pdf = client.get(f"/api/v1/documents/{document_id}/export/pdf", headers=auth_headers)
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")

    dashboard = client.get("/api/v1/dashboard", headers=auth_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["counts"]["documents"] >= 1
