from __future__ import annotations

import hashlib
import logging
import math
import re

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def embedding_base_url() -> str:
    return (settings.embedding_base_url or settings.llm_base_url or "http://localhost:11434").rstrip("/")


def chunk_text(text: str, *, max_chars: int = 700, overlap: int = 120) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + max_chars)
        if end < len(cleaned):
            split_at = cleaned.rfind(". ", start, end)
            if split_at > start + max_chars // 3:
                end = split_at + 1
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def fallback_embed(text: str, dim: int | None = None) -> list[float]:
    """Детерминированный локальный эмбеддинг для тестов и офлайн-режима."""
    size = dim or settings.embedding_dim
    vector = [0.0] * size
    tokens = re.findall(r"[а-яa-z0-9]{2,}", (text or "").lower())
    if not tokens:
        tokens = ["empty"]
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for index in range(0, min(len(digest), 16)):
            bucket = digest[index] % size
            sign = 1.0 if digest[(index + 1) % len(digest)] % 2 == 0 else -1.0
            vector[bucket] += sign
    return _normalize(vector)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    try:
        return [_embed_via_ollama(text) for text in texts]
    except Exception as exc:
        logger.warning("Ollama embeddings unavailable, using fallback: %s", exc)
        return [fallback_embed(text) for text in texts]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]


def _embed_via_ollama(text: str) -> list[float]:
    base = embedding_base_url()
    payload = {"model": settings.embedding_model, "prompt": text}
    with httpx.Client(timeout=settings.embedding_timeout_seconds) as client:
        response = client.post(f"{base}/api/embeddings", json=payload)
        if response.status_code == 404:
            # OpenAI-compatible embeddings endpoint
            response = client.post(
                f"{base}/v1/embeddings",
                json={"model": settings.embedding_model, "input": text},
            )
            response.raise_for_status()
            data = response.json()
            vector = data["data"][0]["embedding"]
        else:
            response.raise_for_status()
            vector = response.json()["embedding"]
    if not isinstance(vector, list) or not vector:
        raise RuntimeError("Пустой embedding")
    return [float(value) for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    size = min(len(left), len(right))
    if size == 0:
        return 0.0
    return sum(left[index] * right[index] for index in range(size))
