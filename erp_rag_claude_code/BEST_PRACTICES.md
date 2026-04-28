# BEST_PRACTICES.md — ChronicCare Backend

> Read this before every coding session. These are hard-won rules, not suggestions.
> Violations will be caught in CI or code review and will block your merge.

---

## 1. FastAPI Patterns

### Router → Service → Repository (strict layering)

```python
# ✅ CORRECT
# app/routers/conversation.py
@router.post("/conversation", response_model=ConversationResponse)
async def create_conversation(
    body: ConversationRequest,
    svc: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    return await svc.process_turn(body)

# app/services/conversation.py
class ConversationService:
    async def process_turn(self, body: ConversationRequest) -> ConversationResponse:
        # All logic lives here
        ...
```

```python
# ❌ WRONG — logic inside router
@router.post("/conversation")
async def create_conversation(body: ConversationRequest):
    symptoms = await gemini_client.extract(body.text)   # NO
    risk = model.predict(symptoms)                       # NO
    return {"risk": risk}
```

### Always use `response_model`

```python
# ✅
@router.post("/score", response_model=RiskScoreResponse)

# ❌
@router.post("/score")  # raw dict returned
```

### Dependency injection for services

```python
# app/dependencies.py
def get_conversation_service(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    gemini: GeminiClient = Depends(get_gemini_client),
) -> ConversationService:
    return ConversationService(db=db, redis=redis, gemini=gemini)
```

---

## 2. Pydantic v2 Models

```python
# ✅ Use model_validator and field_validator (v2 API)
from pydantic import BaseModel, field_validator, model_validator

class FeatureVector(BaseModel):
    symptom_severity_score: float
    glucose_deviation_pct: float
    hours_since_last_meal: float
    hba1c_band: int
    age_band: int
    on_insulin_flag: bool

    @field_validator("symptom_severity_score")
    @classmethod
    def severity_range(cls, v: float) -> float:
        if not 0.0 <= v <= 3.0:
            raise ValueError("symptom_severity_score must be in [0.0, 3.0]")
        return v

# ❌ Never use .dict() — use .model_dump()
# ❌ Never use @validator — use @field_validator
```

---

## 3. Gemini Client

### Always async. Always structured output. Always retry on 503.

```python
# app/services/gemini_client.py
import asyncio
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import google.generativeai as genai
from app.config import settings

class GeminiClient:
    def __init__(self) -> None:
        genai.configure(api_key=settings.gemini_api_key)
        self._model = genai.GenerativeModel("gemini-1.5-flash")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(Exception),
    )
    async def extract_entities(self, de_identified_text: str, glossary: str) -> dict:
        prompt = ENTITY_EXTRACTOR_SYSTEM_PROMPT.format(glossary=glossary)
        response = await asyncio.to_thread(
            self._model.generate_content,
            [prompt, de_identified_text],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
            ),
        )
        return json.loads(response.text)
```

### Never call Gemini more than 2 times per conversation turn.

Call 1 = entity extraction only.
Call 2 = response generation only.

The Decision Tree makes the risk decision — not Gemini.

---

## 4. PII Middleware

### The PII middleware must run before every service call.

```python
# app/middleware/pii.py
class PIIMiddleware(BaseHTTPMiddleware):
    """
    Strips patient name, phone, and national ID from request body.
    Stores token → original mapping in Redis with TTL = 3600s.
    The de-identified body is forwarded to downstream handlers.
    """
    PATTERNS = {
        "name": re.compile(r'"display_name"\s*:\s*"([^"]+)"'),
        "phone": re.compile(r'(\+213\d{9}|\b0\d{9}\b)'),
        "nid": re.compile(r'\b\d{18}\b'),
    }
```

**Test it:**
```python
# tests/unit/test_pii_middleware.py
def test_name_is_stripped(client):
    resp = client.post("/api/v1/conversation", json={
        "patient_id": "uuid",
        "text": "Ahmed Benaissa dit qu'il a mal à la tête"
    })
    # Verify Gemini mock received '[PATIENT]' not 'Ahmed Benaissa'
    assert "Ahmed" not in gemini_mock.last_call_args
```

---

## 5. ML Inference

### Load model once at startup. Never at request time.

```python
# app/main.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.risk_model = joblib.load("ml/models/risk_tree.pkl")
    app.state.redis = await create_redis_pool()
    yield
    # Shutdown
    await app.state.redis.aclose()

app = FastAPI(lifespan=lifespan)
```

### Feature vector must have exactly 6 features in the correct order.

```python
FEATURE_ORDER = [
    "symptom_severity_score",   # float 0–3
    "glucose_deviation_pct",    # float
    "hours_since_last_meal",    # float
    "hba1c_band",               # int 0–3
    "age_band",                 # int 0–2
    "on_insulin_flag",          # bool → int
]

def to_numpy(fv: FeatureVector) -> np.ndarray:
    return np.array([[
        fv.symptom_severity_score,
        fv.glucose_deviation_pct,
        fv.hours_since_last_meal,
        fv.hba1c_band,
        fv.age_band,
        int(fv.on_insulin_flag),
    ]])
```

---

## 6. Notification Pipeline

### All three notification channels fire together on HIGH risk — never partially.

```python
# app/services/notification.py
async def fire_high_risk_alerts(event: RiskEvent, patient: Patient) -> list[str]:
    """Returns list of channels successfully notified."""
    results = await asyncio.gather(
        _send_fcm_push(patient.family_member_ids, event),
        _send_twilio_sms(patient.family_phone, event),
        _send_sendgrid_email(patient.doctor_email, event),
        return_exceptions=True,
    )
    fired = []
    for channel, result in zip(["fcm_family", "sms_family", "email_doctor"], results):
        if not isinstance(result, Exception):
            fired.append(channel)
        else:
            logger.error("Notification failed for channel %s: %s", channel, result)
    return fired
```

**Do not** raise on partial failure — log and continue. Partial alert is better than no alert.

---

## 7. Error Handling

```python
# ✅ Use custom exception classes, not bare Exception
# app/exceptions.py
class GeminiExtractionError(Exception): ...
class FeatureMapperError(Exception): ...
class RiskModelNotLoadedError(Exception): ...

# ✅ Map to HTTP codes in a central exception handler
@app.exception_handler(GeminiExtractionError)
async def gemini_error_handler(request: Request, exc: GeminiExtractionError):
    return JSONResponse(status_code=502, content={"detail": "AI extraction failed", "retry": True})
```

---

## 8. Testing Conventions

```
tests/
├── unit/           ← fast, fully mocked, no network calls
│   ├── test_pii_middleware.py
│   ├── test_feature_mapper.py
│   ├── test_risk_router.py
│   └── test_zscore.py
├── integration/    ← real API keys, marked @pytest.mark.integration
│   ├── test_conversation_flow.py   ← end-to-end HIGH path
│   ├── test_notifications.py
│   └── test_pdf_export.py
└── conftest.py     ← shared fixtures (test client, mock Gemini, seeded DB)
```

**Rule:** Unit tests use `unittest.mock.AsyncMock` for all external calls.
**Rule:** Integration tests are skipped unless `INTEGRATION_TESTS=1` env var is set.

```python
# conftest.py
@pytest.fixture
def mock_gemini(monkeypatch):
    mock = AsyncMock()
    mock.extract_entities.return_value = {
        "symptoms": ["dizziness", "excessive_thirst"],
        "severity_hints": ["since_morning"],
        "missing_fields": [],
        "darija_confidence": 0.94,
    }
    monkeypatch.setattr("app.services.conversation.gemini_client", mock)
    return mock
```

---

## 9. Git Hygiene

- Branch name: `feature/BE-<id>-<short-slug>` or `fix/BE-<id>-<short-slug>`
- Commit format: `<type>(<scope>): <what>` — e.g. `feat(conversation): add follow-up gate logic`
- One logical change per commit — do not batch unrelated changes
- Run `python scripts/start_session.py` before starting, `python scripts/sprint_status.py` before opening a PR
- Never force-push to `develop` or `main`

---

## 10. Performance Contracts

| Operation | Budget | How enforced |
|---|---|---|
| Gemini Call 1 (entity extraction) | < 3s | timeout in GeminiClient |
| Decision Tree inference | < 5ms | assert in integration test |
| Firestore write | < 500ms | timeout in firebase_admin call |
| Total: Darija input → risk badge | < 5s | integration test wall-clock assertion |
| PDF generation | < 5s | integration test wall-clock assertion |
| Demo reset script | < 30s | measured in Sprint 4 DoD |