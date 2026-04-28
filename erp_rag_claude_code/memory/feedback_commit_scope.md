---
name: Commit scope — erp_rag_claude_code excluded
description: Never commit files inside erp_rag_claude_code/ to git
type: feedback
---

Never stage or commit files inside `erp_rag_claude_code/` (agent definitions, sprint plans, memory, docs, scripts).

**Why:** User explicitly rejected a commit that included those files.

**How to apply:** When committing sprint work, stage only files under `src/`, `docker/`, root config files, or other production code paths. Skip `erp_rag_claude_code/**` entirely.
