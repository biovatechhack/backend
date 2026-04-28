from fastapi import FastAPI
from infrastructure.config.settings import settings
from presentation.api.routers.health_route import health_router
from infrastructure.middleware.pii import PiiMiddleware

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)   

# Production middleware
app.add_middleware(PiiMiddleware)

# Production routers only
app.include_router(health_router, prefix="/api/v1")

# ====================== STARTUP ======================
@app.on_event("startup")
async def startup_event():
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} started")
    print(f"   LLM Provider : {settings.LLM_PROVIDER}")
    print(f"   Environment  : {settings.ENVIRONMENT}")

    # Redis health check
    from infrastructure.cache.redis_session import RedisSessionCache
    try:
        pong = await RedisSessionCache.ping()
        print(f"✅ Redis connected → {pong}")
    except Exception as e:
        print(f"⚠️  Redis warning: {e}")

    print("✅ Backend ready for Sprint 1!")