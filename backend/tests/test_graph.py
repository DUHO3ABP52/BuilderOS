from fastapi.testclient import TestClient


def test_project_graph_and_manual_edge(client: TestClient, auth_headers: dict[str, str]) -> None:
    company = client.post(
        "/api/v1/companies",
        headers=auth_headers,
        json={"name": "ООО Граф Заказчик", "kind": "customer", "inn": "7712345678"},
    )
    assert company.status_code == 201, company.text
    supplier = client.post(
        "/api/v1/companies",
        headers=auth_headers,
        json={"name": "ООО Поставщик Связь", "kind": "supplier"},
    )
    assert supplier.status_code == 201, supplier.text

    project = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={
            "name": "ЖК ГрафТест",
            "address": "Москва",
            "customer_id": company.json()["id"],
        },
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    memory = client.post(
        "/api/v1/memory",
        headers=auth_headers,
        json={
            "kind": "fact",
            "key": "warranty",
            "content": "На ЖК ГрафТест гарантия 36 месяцев",
            "project_id": project_id,
        },
    )
    assert memory.status_code == 201, memory.text

    graph = client.get(f"/api/v1/graph/projects/{project_id}", headers=auth_headers)
    assert graph.status_code == 200, graph.text
    body = graph.json()
    assert body["project_name"] == "ЖК ГрафТест"
    assert body["stats"]["nodes"] >= 2
    assert any(node["entity_type"] == "company" for node in body["nodes"])
    assert any(node["entity_type"] == "memory" for node in body["nodes"])
    assert any(edge["relation"] == "has_customer" for edge in body["edges"])

    edge = client.post(
        "/api/v1/graph/edges",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "from_type": "project",
            "from_id": project_id,
            "to_type": "company",
            "to_id": supplier.json()["id"],
            "relation": "related_to",
            "label": "Поставщик фасада",
        },
    )
    assert edge.status_code == 201, edge.text

    graph2 = client.get(f"/api/v1/graph/projects/{project_id}", headers=auth_headers)
    assert graph2.status_code == 200
    assert any(item["relation"] == "related_to" for item in graph2.json()["edges"])


def test_assistant_project_context(client: TestClient, auth_headers: dict[str, str]) -> None:
    project = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"name": "Объект для AI графа", "address": "СПб"},
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    response = client.post(
        "/api/v1/ai/ask",
        headers=auth_headers,
        json={"message": "контекст объекта", "project_id": project_id},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["agent"] == "graph"
    assert body["intent"] == "project_context"
    assert body["data"]["project_id"] == project_id
