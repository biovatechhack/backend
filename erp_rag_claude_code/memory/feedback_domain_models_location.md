---
name: Domain models location for route schemas
description: Request/response Pydantic models for routes must live in src/domain/models/, not inline in route files
type: feedback
---

Request and response Pydantic models (e.g. QueryRequest, QueryResponse) must be placed in `src/domain/models/`, not defined inline inside `src/routes/` files. Import them from domain into the route.

**Why:** Keeps the domain layer as the single authoritative place for all data contracts; route files should only contain HTTP wiring.

**How to apply:** For every new route, create the corresponding request/response models in `src/domain/models/<feature>_models.py`, export them from `src/domain/models/__init__.py`, then import into the route file.
