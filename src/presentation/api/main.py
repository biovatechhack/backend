from fastapi import FastAPI
from infrastructure.config.settings import settings
from infrastructure.intelligence.adapters.deepseek_adapter import DeepSeekAdapter
from presentation.api.routers.health_route import health_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Temporary LLM instance for testing (will be injected properly later)
llm_adapter = DeepSeekAdapter()

# Routers
app.include_router(health_router, prefix="/api/v1")

# ─────────────────────────────────────────────────────────────
# TEMPORARY TEST ENDPOINT (remove or keep after Sprint 1)
# ─────────────────────────────────────────────────────────────
@app.get("/api/v1/test-llm", tags=["test"])
async def test_llm():
    """Quick test that DeepSeek works with real Darija"""
    glossary = {
        "رأسي يدوخ": "dizziness",
        "عطشان بزاف": "excessive_thirst",
        "ما كليتش": "missed_meal"
    }
    result = await llm_adapter.extract_clinical_entities(
        "حاسس بدوخة وعطاش كثير من الصباح", 
        glossary
    )
    return {"status": "success", "extracted": result}