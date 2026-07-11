from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
import app.db.models  # noqa: F401
from app.modules.auth.service import ensure_first_user
from app.modules.knowledge.indexer import start_reindex_background
from app.services import llm as llm_service
from app.services.infrastructure import check_llm, check_qdrant, check_redis
from app.services.seed import seed_default_blocks
from app.services.storage import check_minio


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        ensure_first_user(session)
        seed_default_blocks(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    llm_service.start_llm_warmup_background()
    start_reindex_background(SessionLocal)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.7.0-alpha",
    description="Локальный цифровой сотрудник строительной компании.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"project": settings.app_name, "status": "running", "version": "0.7.0-alpha"}


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "environment": settings.app_env,
        "redis": check_redis(),
        "qdrant": check_qdrant(),
        "minio": check_minio(),
        "llm": check_llm(),
    }
