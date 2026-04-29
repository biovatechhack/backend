from contextlib import asynccontextmanager

from fastapi import FastAPI

from infrastructure.config.settings import settings
from infrastructure.middleware.pii import PiiMiddleware
from infrastructure.scheduler import reload_from_db, scheduler
from infrastructure.supabase.medication_schedule_repository import (
    SupabaseMedicationScheduleRepository,
)
from presentation.api.routers.adherence import adherence_router
from presentation.api.routers.health_route import health_router
from presentation.api.routers.reminders import reminders_router
from presentation.api.routers.report import report_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"{settings.APP_NAME} v{settings.APP_VERSION} started")
    print(f"   LLM Provider : {settings.LLM_PROVIDER}")
    print(f"   Environment  : {settings.ENVIRONMENT}")

    from infrastructure.cache.redis_session import RedisSessionCache
    try:
        pong = await RedisSessionCache.ping()
        print(f"Redis connected -> {pong}")
    except Exception as e:
        print(f"Redis warning: {e}")

    scheduler.start()
    print("Scheduler started")

    try:
        count = await reload_from_db(SupabaseMedicationScheduleRepository())
        print(f"Scheduler: reloaded {count} active reminder(s)")
    except Exception as exc:
        print(f"Scheduler reload warning: {exc}")

    yield

    scheduler.shutdown()
    print("Scheduler stopped")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Production middleware
app.add_middleware(PiiMiddleware)

# Production routers only
app.include_router(health_router, prefix="/api/v1")
app.include_router(reminders_router, prefix="/api/v1")
app.include_router(report_router, prefix="/api/v1")
app.include_router(adherence_router, prefix="/api/v1")