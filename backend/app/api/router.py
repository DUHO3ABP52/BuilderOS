from fastapi import APIRouter

from app.modules.ai.router import router as ai_router
from app.modules.auth.router import router as auth_router
from app.modules.blocks.router import router as blocks_router
from app.modules.calendar.router import router as calendar_router
from app.modules.companies.router import router as companies_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.documents.router import router as documents_router
from app.modules.events.router import router as events_router
from app.modules.finance.router import router as finance_router
from app.modules.graph.router import router as graph_router
from app.modules.knowledge.router import router as knowledge_router
from app.modules.memory.router import router as memory_router
from app.modules.projects.router import router as projects_router
from app.modules.tasks.router import router as tasks_router
from app.modules.templates.router import router as templates_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(dashboard_router)
api_router.include_router(ai_router)
api_router.include_router(companies_router)
api_router.include_router(projects_router)
api_router.include_router(templates_router)
api_router.include_router(documents_router)
api_router.include_router(blocks_router)
api_router.include_router(knowledge_router)
api_router.include_router(tasks_router)
api_router.include_router(finance_router)
api_router.include_router(calendar_router)
api_router.include_router(graph_router)
api_router.include_router(memory_router)
api_router.include_router(events_router)
