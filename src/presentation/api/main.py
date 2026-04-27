from fastapi import FastAPI
from infrastructure.config.settings import settings
from infrastructure.intelligence.adapters.deepseek_adapter import DeepSeekAdapter
from presentation.api.routers.health_route import health_router
from infrastructure.middleware.pii import PiiMiddleware   # ← PII middleware
from infrastructure.cache.redis_session import RedisSessionCache

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# ====================== MIDDLEWARE ======================
app.add_middleware(PiiMiddleware)

# ====================== LLM INSTANCE ======================
llm_adapter = DeepSeekAdapter()   # ← THIS WAS MISSING

# ====================== ROUTERS ======================
app.include_router(health_router, prefix="/api/v1")

# ====================== TEMP TEST ENDPOINT ======================
@app.get("/api/v1/test-llm", tags=["test"])
async def test_llm():
    """Test DeepSeek + PII middleware with real Darija"""
    glossary = {
        "رأسي يدوخ": "dizziness",
        "عطشان بزاف": "excessive_thirst",
        "ما كليتش": "missed_meal"
    }
    
    result = await llm_adapter.extract_clinical_entities(
        "حاسس بدوخة وعطاش كثير من الصباح واسمي Ahmed Benaissa", 
        glossary
    )
    return {"status": "success", "extracted": result}

@app.on_event("startup")
async def startup_event():
    # Existing startup code...
    print("🚀 Starting ChronicCare Nour...")

    # Redis connection test
    try:
        pong = await RedisSessionCache.ping()
        print(f"✅ Redis connected → {pong}")
    except Exception as e:
        print(f"⚠️  Redis connection failed: {e}")

    print("🚀 Backend ready!")

@app.get("/api/v1/test-redis", tags=["test"])
async def test_redis():
    session_id = "test_session_001"
    test_data = {
        "patient_id": "pat_001",
        "turns": [],
        "current_risk": "LOW",
        "last_updated": "2026-04-27T23:00:00"
    }

    await RedisSessionCache.set_session(session_id, test_data)
    retrieved = await RedisSessionCache.get_session(session_id)

    return {
        "status": "success",
        "redis_works": True,
        "session_id": session_id,
        "data": retrieved
    }