from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0-alpha",
    description="Локальный цифровой сотрудник строительной компании.",
    lifespan=lifespan,
)
app.include_router(api_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}
