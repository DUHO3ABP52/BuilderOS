from fastapi import APIRouter

from app.modules.companies.router import router as companies_router
from app.modules.projects.router import router as projects_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(companies_router)
api_router.include_router(projects_router)
