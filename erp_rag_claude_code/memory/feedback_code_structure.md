---
name: Code structure preferences
description: How the user expects code to be structured — imports, helpers, domain entities
type: feedback
---

Always organise new modules following these rules:

1. **All imports at the top of the file** — never inside methods or functions, even for optional dependencies. Use a module-level `try/except ImportError` with a boolean flag (`_LIB_AVAILABLE = False`) when a dependency is optional.

2. **Helper functions go in a dedicated helpers folder** — when a module (e.g., a chunker) needs utility functions (regex, summary builders, format detectors), create a `helpers/` sub-package next to it and split helpers into focused files (e.g., `table_helpers.py`, `text_helpers.py`). Do not define helpers as module-level functions inside the main file.

3. **Entity/dataclasses belong in `src/domain/`** — any dataclass or named entity that represents a concept (even an infrastructure-adapter concept like `TableElement`) must live in the domain layer, not inline inside infrastructure files.

**Why:** keeps each file to a single responsibility, makes imports traceable, and keeps the domain layer the single source of truth for data shapes.

**How to apply:** whenever writing a new infrastructure class that needs helpers or data shapes, create the domain dataclass first, the helpers folder second, then the main class last.
