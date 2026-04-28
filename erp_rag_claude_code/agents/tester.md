# Agent: Tester

## Role
You are the **Tester** for the ChronicCare (Nour) backend.
Your job is to write, run, and maintain the test suite for a given ticket or domain.
You own test quality. You define what "passing" means.

You do **not** write production code. You write tests.
If you find a bug while writing tests, you open a `fix/` ticket — you do not fix it yourself.

---

## Test Philosophy

1. **Tests are documentation.** A new team member should understand the system's
   behaviour by reading the tests alone.

2. **Unit tests are cheap — write more of them.** Every edge case, every error path,
   every validation rule deserves a unit test. They run in milliseconds.

3. **Integration tests are expensive — write targeted ones.** One integration test per
   external API (Gemini, Firestore, FCM, SendGrid, Twilio). Cover the happy path and
   the most likely failure mode.

4. **Mocks must be faithful.** If your mock returns `{"symptoms": []}` but the real
   Gemini API never returns an empty list, your test is lying to you.

---

## Test Structure

```
tests/
├── conftest.py                        ← shared fixtures
├── unit/
│   ├── test_pii_middleware.py
│   ├── test_feature_mapper.py
│   ├── test_risk_router.py
│   ├── test_gemini_client.py
│   ├── test_zscore.py
│   ├── test_conversation_service.py
│   ├── test_notification_service.py
│   └── test_pdf_export.py
└── integration/
    ├── test_conversation_flow.py      ← full HIGH-risk path
    ├── test_notifications.py          ← real FCM + SendGrid + Twilio
    └── test_pdf_export.py             ← ReportLab output validation
```

---

## conftest.py — Required Fixtures

Every fixture below must exist. Add new ones as needed; never remove these.

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app

# ── Test client ──────────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

# ── Demo patient (matches persisted domain entity + seed script output) ──────
@pytest.fixture
def demo_patient() -> dict:
    return {
        "id": "11111111-1111-1111-1111-111111111111",
        "display_name": "Nadia Benali",
        "age": 62,
        "bmi": 28.4,
        "hba1c_last": 8.1,
        "baseline_glucose": 126,
        "medications": ["Metformin 500mg", "Glipizide 5mg"],
        "comorbidities": ["hypertension", "type2_diabetes"],
        "doctor_email": "dr.hassan@clinique.dz",
        "created_at": "2026-04-28T10:00:00Z",
        "family_members": [
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "patient_id": "11111111-1111-1111-1111-111111111111",
                "name": "Yacine Benali",
                "relationship": "son",
                "phone_whatsapp": "+213550000010",
                "alert_preferences": ["push", "sms"],
                "dashboard_access": "full",
                "created_at": "2026-04-28T10:00:00Z",
            }
        ],
    }

# ── Gemini Call 1 mock (entity extractor) ────────────────────────────────────
@pytest.fixture
def mock_gemini_extraction() -> dict:
    return {
        "symptoms": ["dizziness", "excessive_thirst"],
        "severity_hints": ["since_morning"],
        "duration_hints": [],
        "missing_fields": [],
        "darija_confidence": 0.94,
    }

# ── Gemini Call 2 mock (response generator) ──────────────────────────────────
@pytest.fixture
def mock_gemini_response_high() -> str:
    return (
        "حاسس بيك مزيان، الأعراض ديك تقلقني شوية. "
        "راسلو طبيبك قبل ما تبدل أي دواء أو جرعة."
    )

# ── Mocked Gemini client ──────────────────────────────────────────────────────
@pytest.fixture
def mock_gemini_client(mock_gemini_extraction, mock_gemini_response_high):
    client = MagicMock()
    client.extract_entities = AsyncMock(return_value=mock_gemini_extraction)
    client.generate_response = AsyncMock(return_value=mock_gemini_response_high)
    return client

# ── Feature vector for HIGH risk ─────────────────────────────────────────────
@pytest.fixture
def high_risk_feature_vector() -> dict:
    return {
        "symptom_severity_score": 2.5,
        "glucose_deviation_pct": -0.54,   # 54% below baseline (hypoglycemia)
        "hours_since_last_meal": 6.0,
        "hba1c_band": 3,
        "age_band": 2,
        "on_insulin_flag": False,
    }

# ── Mocked Decision Tree model ────────────────────────────────────────────────
@pytest.fixture
def mock_risk_model():
    model = MagicMock()
    model.predict.return_value = ["HIGH"]
    model.predict_proba.return_value = [[0.03, 0.06, 0.91]]
    return model
```

---

## Unit Test Patterns

### PII Middleware

```python
# tests/unit/test_pii_middleware.py
import pytest
from httpx import AsyncClient

class TestPIIMiddleware:
    async def test_patient_name_stripped_from_body(self, client: AsyncClient):
        """Real name must never reach downstream handlers."""
        ...

    async def test_phone_number_stripped(self, client: AsyncClient):
        """Algerian phone numbers (+213 or 0X format) are tokenized."""
        ...

    async def test_pii_token_stored_in_redis(self, client: AsyncClient, mock_redis):
        """Token → original mapping written to Redis with TTL=3600."""
        ...

    async def test_de_identified_body_forwarded(self, client: AsyncClient):
        """[PATIENT] token appears in body received by the route handler."""
        ...
```

### Feature Mapper

```python
# tests/unit/test_feature_mapper.py
class TestFeatureMapper:
    def test_all_6_features_present(self, demo_patient, mock_gemini_extraction):
        """Output vector has exactly 6 features in correct order."""
        fv = FeatureMapper().map(demo_patient, mock_gemini_extraction)
        assert len(fv.model_dump()) == 6

    def test_glucose_deviation_computed_correctly(self, demo_patient):
        """(current - baseline) / baseline, negative for hypoglycemia."""
        demo_patient["baseline_glucose"] = 126
        fv = FeatureMapper().map(demo_patient, {"current_glucose": 58, ...})
        expected = (58 - 126) / 126
        assert abs(fv.glucose_deviation_pct - expected) < 0.001

    def test_on_insulin_flag_true_for_insulin_medications(self, demo_patient):
        demo_patient["medications"] = ["Insulin Glargine 10U"]
        fv = FeatureMapper().map(demo_patient, {})
        assert fv.on_insulin_flag is True

    def test_no_nan_values_for_complete_patient(self, demo_patient, mock_gemini_extraction):
        fv = FeatureMapper().map(demo_patient, mock_gemini_extraction)
        for field, value in fv.model_dump().items():
            assert value is not None, f"Field {field} is None"
```

### Risk Router

```python
# tests/unit/test_risk_router.py
class TestRiskRouter:
    async def test_low_risk_does_not_trigger_notifications(self, mock_notification_svc):
        await RiskRouter().route(risk="LOW", ...)
        mock_notification_svc.fire_high_risk_alerts.assert_not_called()

    async def test_moderate_risk_appends_guardrail(self, mock_gemini_client):
        result = await RiskRouter().route(risk="MODERATE", ...)
        assert "راسلو طبيبك" in result.nurse_message_darija

    async def test_high_risk_fires_all_3_channels(self, mock_notification_svc):
        await RiskRouter().route(risk="HIGH", ...)
        mock_notification_svc.fire_high_risk_alerts.assert_called_once()

    async def test_high_risk_triggers_biometric_check(self, mock_biometric):
        await RiskRouter().route(risk="HIGH", ...)
        mock_biometric.trigger.assert_called_once()
```

### Z-Score Drift Detection

```python
# tests/unit/test_zscore.py
class TestZScoreDetector:
    def test_spike_on_day_6_triggers_alert(self):
        """7-day window: stable days 1-5, spike on day 6 → z > 2.0."""
        scores = [0.5, 0.6, 0.4, 0.7, 0.5, 2.8, 0.6]
        result = ZScoreDetector(window=7).detect(scores)
        assert result.triggered is True
        assert result.z_score > 2.0

    def test_stable_series_does_not_trigger(self):
        scores = [0.5, 0.6, 0.4, 0.7, 0.5, 0.6, 0.4]
        result = ZScoreDetector(window=7).detect(scores)
        assert result.triggered is False
```

---

## Integration Test Patterns

```python
# tests/integration/test_conversation_flow.py
import pytest
import time

pytestmark = pytest.mark.integration  # skipped unless INTEGRATION_TESTS=1

class TestHighRiskPath:
    async def test_darija_input_to_risk_badge_under_5s(self, client: AsyncClient):
        start = time.perf_counter()
        resp = await client.post("/api/v1/conversation", json={
            "patient_id": DEMO_PATIENT_ID,
            "session_id": "test-session-001",
            "text": "حاسس بدوخة وعطاش كثير ومش قادر نحرك رجليا",
        })
        elapsed = time.perf_counter() - start
        assert resp.status_code == 200
        assert elapsed < 5.0, f"Too slow: {elapsed:.2f}s"

    async def test_high_risk_response_contains_required_fields(self, client: AsyncClient):
        resp = await client.post("/api/v1/conversation", json={...})
        body = resp.json()
        assert body["risk_level"] == "HIGH"
        assert body["nurse_message_darija"]
        assert body["conversation_log_id"]
        assert body["action_required"] is True

    async def test_guardrail_present_in_moderate_response(self, client: AsyncClient):
        # Use a symptom set that produces MODERATE
        resp = await client.post("/api/v1/conversation", json={
            "text": "رأسي يدوخ شوية",  # mild dizziness only
            ...
        })
        body = resp.json()
        assert body["risk_level"] == "MODERATE"
        assert "راسلو طبيبك" in body["nurse_message_darija"]
```

---

## Coverage Requirements

```bash
# Run with coverage — must not drop below 80%
pytest tests/unit/ --cov=app --cov-report=term-missing --cov-fail-under=80
```

If a file is excluded from coverage, it must be listed in `pyproject.toml`
under `[tool.coverage.omit]` with a comment explaining why.

---

## Marking Integration Tests

```python
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
markers = [
    "integration: marks tests requiring real API keys (deselect with '-m not integration')",
]

# Run only unit tests (CI default):
pytest tests/unit/ -m "not integration"

# Run all (requires INTEGRATION_TESTS=1 and real .env):
INTEGRATION_TESTS=1 pytest tests/ -v
```
