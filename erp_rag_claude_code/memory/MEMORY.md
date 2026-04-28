# Memory Index

- [Commit message style](feedback_commit_style.md) — No Co-Authored-By signature in commits; keep only relevant change descriptions
- [Sprint close PR flow](feedback_sprint_close_flow.md) — Push branch → open PR → merge via PR; never merge locally before opening the PR
- [No Claude Code signature in PRs](feedback_no_claude_code_signature.md) — Omit the "🤖 Generated with Claude Code" footer from all PR bodies
- [CI gap blocks sprint merges](project_ci_gap.md) — No requirements.txt at root; hold merge/tag/branch-delete until CI is defined and green
- [All work via pull requests](feedback_all_work_via_pr.md) — Never push directly to sprint/develop; every commit must go through a PR on a short-lived branch
- [Clean Architecture for every task](feedback_clean_architecture_tasks.md) — Domain models → ports → infrastructure → use cases → thin task file; apply for every feature, not just workers
- [Python env activation](feedback_env_activation.md) — Use `source erp-rag-env-v2/bin/activate`; never conda or system Python
- [Chunk dataclass belongs in domain](feedback_chunk_dataclass_domain.md) — Dataclasses for pipeline outputs live in src/domain/, not in workers/infrastructure
- [Code structure preferences](feedback_code_structure.md) — All imports at top; helpers in a helpers/ sub-package; entity dataclasses in src/domain/
- [Embed pipeline order](feedback_embed_pipeline.md) — chunk first → embed each chunk with its metadata; never embed the whole asset as one unit
- [Implement tasks one at a time](feedback_task_by_task.md) — Executor must implement sprint tasks one by one, not batch multiple task implementations in a single pass
