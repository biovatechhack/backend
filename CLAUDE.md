# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**ChronicCare Nour** — FastAPI backend for AI-assisted diabetic patient monitoring. Patients speak in Darija; Gemini extracts clinical entities; an EBM classifier predicts risk level (low / moderate / high); HIGH-risk events trigger multi-channel notifications (FCM, email, SMS).

## Environment

The virtualenv is at `hackathon-env/` (Python 3.13). Always use it explicitly:

```bash
hackathon-env/bin/python
hackathon-env/bin/pip
```

`src/` is the Python path root. **All commands that import project code must be run from the `src/` directory**, because `pyrightconfig.json` and the module layout treat `src/` as the package root (no `src.` prefix in imports).

## Commands

```bash
# Run the API server
cd src && ../hackathon-env/bin/python -m uvicorn presentation.api.main:app --reload

# Run all unit tests
cd src && ../hackathon-env/bin/python -m pytest tests/unit/ -v

# Run a single test file
cd src && ../hackathon-env/bin/python -m pytest tests/unit/test_risk_classifier.py -v

# Run integration tests (requires running API + Redis)
cd src && ../hackathon-env/bin/python -m pytest tests/integration/ -v

# Lint
hackathon-env/bin/ruff check src/

# Type-check
hackathon-env/bin/mypy src/ --strict

# Database migrations
cd src && ../hackathon-env/bin/alembic upgrade head
cd src && ../hackathon-env/bin/alembic revision --autogenerate -m "description"

# Seed demo data
cd src && ../hackathon-env/bin/python scripts/seed_demo_data.py

# Retrain the EBM model (saves to models/risk_ebm.pkl)
hackathon-env/bin/python src/scripts/train_risk_ebm.py
```

## Architecture

Hexagonal (ports & adapters). The dependency rule flows inward: `presentation → application → domain ← abstraction ← infrastructure`.

```
src/
  domain/           # Zero dependencies. Pure Python dataclasses (entities/) and Pydantic models (models/)
  abstraction/      # ABCs only. ports/llm_port.py, ports/risk_port.py — interfaces the app depends on
  application/      # Use cases (orchestration). Depends only on domain + abstraction
  infrastructure/   # Concrete implementations. Depends on everything
    config/         # Pydantic Settings, reads .env
    database/       # SQLAlchemy async models + session factory (SQLite via aiosqlite)
    intelligence/   # GeminiClient (implements LlmPort), DeepSeek adapter
    ml/             # RiskClassifier (implements RiskClassifierPort); model at models/risk_ebm.pkl
    notifications/  # FCM / SendGrid / Twilio adapters (in progress)
    middleware/      # PiiMiddleware — strips Algerian names/phones before any LLM call
  presentation/
    api/            # FastAPI app + routers; each feature gets its own router file
  migrations/       # Alembic. env.py wires settings.SQLITE_URL at runtime
  scripts/          # One-off: seed_demo_data.py, train_risk_ebm.py
  tests/
    unit/           # No I/O. conftest.py has demo_patient and mock_gemini_client fixtures
    integration/    # Hits real FastAPI (TestClient) + Redis
```

### Key design decisions

**Domain entities vs ORM models** — `domain/entities/` are pure dataclasses used throughout the app. `infrastructure/database/models.py` are SQLAlchemy ORM models. They are separate types; mapping between them happens in repository adapters.

**EBM classifier** — `RiskFeatures` has 15 fields (age, gender, bmi, hba1c, has_hypertension, has_heart_disease, medication_count, glucose, hr, spo2, steps, sleep_hours, confusion, tremors, thirst). The feature order in `risk_classifier.py::FEATURE_NAMES` must exactly match `train_risk_ebm.py::FEATURE_NAMES`. The model file path resolves as `Path(__file__).parents[3] / "models" / "risk_ebm.pkl"`.

**Settings** — `infrastructure/config/settings.py` reads `.env`. Copy `.env.example` to `.env` for local dev. All settings are accessed via the singleton `from infrastructure.config.settings import settings`.

**LLM output shape** — `GeminiClient.extract_entities()` returns `EntityExtractionResult(medications, symptoms, vital_signs, risk_flags)`. The feature mapper (`infrastructure/ml/feature_mapper.py`) combines this with patient profile + sensor vitals to build `RiskFeatures`.

**PII middleware** — active on `/conversation` and `/test-llm` paths only. Replaces Algerian full names, phone numbers (0[5-7]XXXXXXXX), and long numeric IDs with tokens before any downstream processing.

### Branch and commit conventions

Follow the agent spec in `erp_rag_claude_code/{agents,scripts,docs}/agents/committer.md`:
- Branch names: `feature/BE-<id>-<slug>` or `fix/BE-<id>-<slug>`
- Commit scopes: `conversation` · `ml` · `risk` · `notif` · `db` · `cache` · `pii` · `infra` · `config`
- Merge strategy: merge commit (no squash); `main ← master` via PR

### Known test issues (as of sprint 1)

`test_risk_classifier.py` and `test_risk_models.py` have stale fixtures that were written before `gender` and `bmi` were added to `RiskFeatures` (BE-05). Update fixtures to include those fields before those tests will pass.
