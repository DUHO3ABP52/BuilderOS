from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid5

from app.core.config import settings
from app.services.embeddings import chunk_text, cosine_similarity, embed_query, embed_texts, fallback_embed

logger = logging.getLogger(__name__)

_memory_lock = threading.Lock()
_memory_store: dict[str, dict[str, Any]] = {}
_vector_size: int | None = None


@dataclass(frozen=True)
class RagHit:
    item_id: UUID
    score: float
    chunk: str
    title: str
    category: str


def rag_is_enabled() -> bool:
    return bool(settings.rag_enabled)


def _collection_name() -> str:
    return settings.rag_collection


def _point_id(item_id: UUID, chunk_index: int) -> str:
    return str(uuid5(item_id, f"chunk-{chunk_index}"))


def _resolved_vector_size(sample: list[float] | None = None) -> int:
    global _vector_size
    if sample:
        _vector_size = len(sample)
    return _vector_size or settings.embedding_dim


def _qdrant_client():
    from qdrant_client import QdrantClient

    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=5)


def ensure_collection(vector_size: int | None = None) -> bool:
    if not rag_is_enabled():
        return False
    size = vector_size or _resolved_vector_size()
    try:
        from qdrant_client.http import models as qmodels

        client = _qdrant_client()
        names = {item.name for item in client.get_collections().collections}
        if _collection_name() not in names:
            client.create_collection(
                collection_name=_collection_name(),
                vectors_config=qmodels.VectorParams(size=size, distance=qmodels.Distance.COSINE),
            )
        return True
    except Exception as exc:
        logger.warning("Qdrant ensure_collection failed: %s", exc)
        return False


def upsert_knowledge_item(*, item_id: UUID, title: str, category: str, content: str) -> int:
    chunks = chunk_text(f"{title}. {content}")
    if not chunks:
        delete_knowledge_item(item_id)
        return 0

    vectors = embed_texts(chunks)
    _resolved_vector_size(vectors[0])
    payloads = [
        {
            "item_id": str(item_id),
            "title": title,
            "category": category,
            "chunk": chunk,
            "chunk_index": index,
        }
        for index, chunk in enumerate(chunks)
    ]

    if _upsert_qdrant(item_id, vectors, payloads):
        return len(chunks)

    _upsert_memory(item_id, vectors, payloads)
    return len(chunks)


def delete_knowledge_item(item_id: UUID) -> None:
    try:
        from qdrant_client.http import models as qmodels

        client = _qdrant_client()
        client.delete(
            collection_name=_collection_name(),
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="item_id",
                            match=qmodels.MatchValue(value=str(item_id)),
                        )
                    ]
                )
            ),
        )
    except Exception as exc:
        logger.debug("Qdrant delete skipped: %s", exc)

    with _memory_lock:
        stale = [key for key, value in _memory_store.items() if value["payload"].get("item_id") == str(item_id)]
        for key in stale:
            _memory_store.pop(key, None)


def search(query: str, *, limit: int | None = None) -> list[RagHit]:
    if not query.strip():
        return []
    top_k = limit or settings.rag_top_k
    vector = embed_query(query)
    hits = _search_qdrant(vector, top_k)
    if hits is None:
        hits = _search_memory(vector, top_k)
    return [hit for hit in hits if hit.score >= settings.rag_score_threshold][:top_k]


def reindex_items(items: list[dict[str, Any]]) -> dict[str, int]:
    ensure_collection()
    indexed = 0
    chunks = 0
    for item in items:
        count = upsert_knowledge_item(
            item_id=item["id"],
            title=item["title"],
            category=item["category"],
            content=item["content"],
        )
        if count:
            indexed += 1
            chunks += count
    return {"items": indexed, "chunks": chunks}


def status_payload() -> dict[str, Any]:
    qdrant_ok = False
    points = 0
    try:
        client = _qdrant_client()
        names = {item.name for item in client.get_collections().collections}
        qdrant_ok = _collection_name() in names
        if qdrant_ok:
            info = client.get_collection(_collection_name())
            points = int(info.points_count or 0)
    except Exception:
        qdrant_ok = False
    with _memory_lock:
        memory_points = len(_memory_store)
    return {
        "enabled": settings.rag_enabled,
        "collection": _collection_name(),
        "qdrant": "ok" if qdrant_ok else "unavailable",
        "points": points,
        "memory_points": memory_points,
        "embedding_model": settings.embedding_model,
        "embedding_dim": _resolved_vector_size(),
        "mode": "qdrant" if qdrant_ok else ("memory" if memory_points else "idle"),
    }


def _upsert_qdrant(item_id: UUID, vectors: list[list[float]], payloads: list[dict[str, Any]]) -> bool:
    try:
        from qdrant_client.http import models as qmodels

        if not ensure_collection(vector_size=len(vectors[0])):
            return False
        # удаляем старые точки item_id только в qdrant, память трогаем отдельно
        client = _qdrant_client()
        client.delete(
            collection_name=_collection_name(),
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="item_id",
                            match=qmodels.MatchValue(value=str(item_id)),
                        )
                    ]
                )
            ),
        )
        points = [
            qmodels.PointStruct(
                id=_point_id(item_id, index),
                vector=vector,
                payload=payload,
            )
            for index, (vector, payload) in enumerate(zip(vectors, payloads, strict=True))
        ]
        client.upsert(collection_name=_collection_name(), points=points)
        return True
    except Exception as exc:
        logger.warning("Qdrant upsert failed: %s", exc)
        return False


def _upsert_memory(item_id: UUID, vectors: list[list[float]], payloads: list[dict[str, Any]]) -> None:
    with _memory_lock:
        stale = [key for key, value in _memory_store.items() if value["payload"].get("item_id") == str(item_id)]
        for key in stale:
            _memory_store.pop(key, None)
        for index, (vector, payload) in enumerate(zip(vectors, payloads, strict=True)):
            _memory_store[_point_id(item_id, index)] = {"vector": vector, "payload": payload}


def _search_qdrant(vector: list[float], limit: int) -> list[RagHit] | None:
    try:
        client = _qdrant_client()
        results = client.search(
            collection_name=_collection_name(),
            query_vector=vector,
            limit=limit,
            with_payload=True,
        )
        hits: list[RagHit] = []
        for point in results:
            payload = point.payload or {}
            hits.append(
                RagHit(
                    item_id=UUID(str(payload["item_id"])),
                    score=float(point.score or 0.0),
                    chunk=str(payload.get("chunk") or ""),
                    title=str(payload.get("title") or ""),
                    category=str(payload.get("category") or ""),
                )
            )
        return hits
    except Exception as exc:
        logger.debug("Qdrant search failed: %s", exc)
        return None


def _search_memory(vector: list[float], limit: int) -> list[RagHit]:
    scored: list[RagHit] = []
    with _memory_lock:
        for item in _memory_store.values():
            payload = item["payload"]
            score = cosine_similarity(vector, item["vector"])
            scored.append(
                RagHit(
                    item_id=UUID(str(payload["item_id"])),
                    score=score,
                    chunk=str(payload.get("chunk") or ""),
                    title=str(payload.get("title") or ""),
                    category=str(payload.get("category") or ""),
                )
            )
    scored.sort(key=lambda hit: hit.score, reverse=True)
    # dedupe by item, keep best chunk
    best: dict[UUID, RagHit] = {}
    for hit in scored:
        current = best.get(hit.item_id)
        if current is None or hit.score > current.score:
            best[hit.item_id] = hit
    return sorted(best.values(), key=lambda hit: hit.score, reverse=True)[:limit]


def warmup_embedding_model() -> None:
    """Прогрев/проверка эмбеддингов (fallback всегда доступен)."""
    try:
        vector = embed_query("проверка индекса BuilderOS")
        _resolved_vector_size(vector)
    except Exception:
        fallback_embed("проверка")
