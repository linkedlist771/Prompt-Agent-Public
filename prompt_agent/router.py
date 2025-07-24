from fastapi import APIRouter

from prompt_agent.api_key.api_key_router import router as api_key_router
from prompt_agent.openai_api.openai_api_router import \
    router as openai_api_router
from prompt_agent.routers.dashboard.router import router as dashboard_router
# from prompt_agent.routers.cookie.router import router as cookie_router
from prompt_agent.routers.health.router import router as health_router
from prompt_agent.vector_db.prompt_vector_db_router import \
    router as prompt_vector_db_router

router = APIRouter(prefix="/api/v1")
# router.include_router(cookie_router, prefix="/cookie", tags=["cookie"])
router.include_router(health_router, prefix="/health", tags=["health"])
router.include_router(prompt_vector_db_router, prefix="/prompt_db", tags=["prompt_db"])
router.include_router(openai_api_router, prefix="", tags=["openai"])
router.include_router(api_key_router, prefix="/api_key", tags=["api_key"])
router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
