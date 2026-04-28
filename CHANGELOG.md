# CHANGELOG — ChronicCare (Nour) Backend

All notable changes are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased] — Sprint 1 (H0–H8): Bootstrap & Infrastructure

### Added — BE-01 SQLite schema, domain entities, seed script

- `pyproject.toml` — project manifest; `uv`-compatible dependency groups; pytest, ruff, mypy configured
- `alembic.ini` + `migrations/` — Alembic setup; migration `20260427_0001` creates all 6 clinical tables
- `src/domain/entities/` — pure Python dataclasses (`slots=True`) for `Patient`, `FamilyMember`, `ConversationLog`, `ConversationTurn`, `RiskEvent`, `MedicationLog`
- `src/infrastructure/database/base.py` — SQLAlchemy `DeclarativeBase`
- `src/infrastructure/database/models.py` — ORM models for all 6 tables; cascade deletes; JSON columns for list fields
- `src/infrastructure/database/session.py` — async engine + `SessionFactory` wired to `settings.SQLITE_URL`
- `src/infrastructure/config/settings.py` — Pydantic `Settings`; reads from `.env`; defaults for local dev
- `scripts/seed_demo_data.py` — idempotent seed: demo patient Nadia Benali + 2 family members + 2 medication logs + 1 HIGH-risk conversation log + 1 risk event
- `.env.example` — full variable reference; no real credentials committed

### Fixed
- `src/infrastructure/database/models.py` — `FamilyMemberModel.relationship` column shadowed the imported `relationship` ORM function; fixed by aliasing `from sqlalchemy.orm import relationship as sa_relationship`

### Tested — 64 unit tests, all green
- `tests/unit/test_domain_entities.py` — all 6 entity dataclasses: fields, defaults, slots, mutable default isolation
- `tests/unit/test_database_models.py` — table registration, column sets, relationships, cascade config, JSON types, nullable constraints
- `tests/unit/test_database_session.py` — async CRUD, UUID/timestamp auto-generation, JSON round-trip, selectinload traversal, cascade delete
- `tests/unit/test_settings.py` — config defaults and env-var overrides
- `tests/unit/test_seed_demo_data.py` — demo data integrity + idempotency guard
