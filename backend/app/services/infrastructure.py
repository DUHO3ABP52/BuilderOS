from app.core.config import settings
from app.services import llm as llm_service


def check_redis() -> str:
    try:
        import redis

        client = redis.from_url(settings.redis_url, socket_connect_timeout=1)
        client.ping()
        return "ok"
    except Exception:
        return "unavailable"


def check_qdrant() -> str:
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=1)
        client.get_collections()
        return "ok"
    except Exception:
        return "unavailable"


def check_llm() -> str:
    return llm_service.check_llm()
