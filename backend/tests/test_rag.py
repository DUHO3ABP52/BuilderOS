from uuid import uuid4

from app.services.embeddings import chunk_text, cosine_similarity, fallback_embed
from app.services import rag as rag_service


def test_chunk_text_splits_long_content() -> None:
    text = "Первое предложение. " * 80
    chunks = chunk_text(text, max_chars=120, overlap=20)
    assert len(chunks) > 1
    assert all(chunk for chunk in chunks)


def test_fallback_embed_is_deterministic() -> None:
    left = fallback_embed("гарантийный срок подрядчика")
    right = fallback_embed("гарантийный срок подрядчика")
    other = fallback_embed("организация строительного производства")
    assert left == right
    assert cosine_similarity(left, right) > 0.99
    assert cosine_similarity(left, other) < cosine_similarity(left, right)


def test_memory_rag_search_ranks_relevant_item() -> None:
    first_id = uuid4()
    second_id = uuid4()
    rag_service.upsert_knowledge_item(
        item_id=first_id,
        title="Гарантийные обязательства",
        category="internal",
        content="Гарантийный срок на общестроительные работы составляет 24 месяца.",
    )
    rag_service.upsert_knowledge_item(
        item_id=second_id,
        title="КС-2",
        category="internal",
        content="КС-2 фиксирует выполненные работы за отчетный период.",
    )
    hits = rag_service.search("какой гарантийный срок", limit=5)
    assert hits
    assert hits[0].item_id == first_id
    assert hits[0].score >= hits[-1].score


def test_knowledge_search_and_reindex_api(client, auth_headers) -> None:
    reindex = client.post("/api/v1/knowledge/reindex", headers=auth_headers)
    assert reindex.status_code == 200, reindex.text
    assert reindex.json()["items"] >= 1

    search = client.get("/api/v1/knowledge/search", headers=auth_headers, params={"q": "гарантийный срок"})
    assert search.status_code == 200, search.text
    body = search.json()
    assert body["count"] >= 1
    assert any(
        "гарант" in item["title"].lower() or "гарант" in (item["excerpt"] or "").lower()
        for item in body["items"]
    )

    status = client.get("/api/v1/knowledge/rag-status", headers=auth_headers)
    assert status.status_code == 200
    assert status.json()["enabled"] is True
