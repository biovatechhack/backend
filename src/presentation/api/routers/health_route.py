from fastapi import APIRouter
from infrastructure.config.settings import settings

health_router = APIRouter(tags=["health"])

@health_router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "llm_provider": settings.LLM_PROVIDER,
        "model_loaded": True   # we will load ML model later
    }