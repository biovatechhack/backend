from __future__ import annotations

from importlib import import_module
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def client():
    """ASGI test client when the application entrypoint exists.

    The tester guide expects this fixture to exist. Until the FastAPI app is
    implemented, tests that depend on it should skip rather than fail at import
    time.
    """
    try:
        httpx = import_module("httpx")
        main_module = import_module("app.main")
    except ModuleNotFoundError as exc:
        pytest.skip(f"ASGI app fixture unavailable: {exc.name} is not installed or not implemented")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main_module.app),
        base_url="http://test",
    ) as async_client:
        yield async_client


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


@pytest.fixture
def mock_gemini_extraction() -> dict:
    return {
        "symptoms": ["dizziness", "excessive_thirst"],
        "severity_hints": ["since_morning"],
        "duration_hints": [],
        "missing_fields": [],
        "darija_confidence": 0.94,
    }


@pytest.fixture
def mock_gemini_response_high() -> str:
    return (
        "حاسس بيك مزيان، الأعراض ديك تقلقني شوية. "
        "راسلو طبيبك قبل ما تبدل أي دواء أو جرعة."
    )


@pytest.fixture
def mock_gemini_client(mock_gemini_extraction, mock_gemini_response_high):
    client = MagicMock()
    client.extract_entities = AsyncMock(return_value=mock_gemini_extraction)
    client.generate_response = AsyncMock(return_value=mock_gemini_response_high)
    return client


@pytest.fixture
def high_risk_feature_vector() -> dict:
    return {
        "symptom_severity_score": 2.5,
        "glucose_deviation_pct": -0.54,
        "hours_since_last_meal": 6.0,
        "hba1c_band": 3,
        "age_band": 2,
        "on_insulin_flag": False,
    }


@pytest.fixture
def mock_risk_model():
    model = MagicMock()
    model.predict.return_value = ["HIGH"]
    model.predict_proba.return_value = [[0.03, 0.06, 0.91]]
    return model
