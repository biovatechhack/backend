---
name: Implement tasks one at a time
description: Executor must implement sprint tasks one by one, not batch multiple task implementations in a single pass
type: feedback
---

Implement one sprint task at a time — write the code, run the tests, then move to the next task.

**Why:** Mixing implementations of multiple tasks in one pass makes it hard to review each task's contribution, debug failures, and commit cleanly per task.

**How to apply:** When executing a sprint plan, implement Task N fully (code + tests), verify it works, commit, then start Task N+1. Never interleave code from two different tasks in the same edit pass.
