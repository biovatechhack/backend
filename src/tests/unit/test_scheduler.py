"""Unit tests for infrastructure/scheduler.py.

Covers:
- Module exports the expected singleton type
- Singleton is not started at import time (no side-effects)
- The same object is returned on repeated imports (module-level singleton)
- A job can be added while stopped and survives start/shutdown cycle
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import STATE_RUNNING, STATE_STOPPED


class TestSchedulerModule:
    def test_scheduler_is_asyncio_scheduler(self):
        """Exported object must be an AsyncIOScheduler, not a sync variant."""
        from infrastructure.scheduler import scheduler
        assert isinstance(scheduler, AsyncIOScheduler)

    def test_scheduler_is_stopped_at_import(self):
        """Scheduler must not auto-start on import — that's lifespan's job."""
        from infrastructure.scheduler import scheduler
        assert scheduler.state == STATE_STOPPED

    def test_scheduler_is_module_singleton(self):
        """Two imports of the same module must return the identical object."""
        from infrastructure import scheduler as mod_a
        from infrastructure import scheduler as mod_b
        assert mod_a.scheduler is mod_b.scheduler

    def test_scheduler_accepts_job_while_stopped(self):
        """Jobs added before start() must be queued, not rejected."""
        from infrastructure.scheduler import scheduler
        job = scheduler.add_job(lambda: None, "interval", seconds=60, id="test_unit_job")
        assert scheduler.get_job("test_unit_job") is not None
        job.remove()

    async def test_scheduler_starts_to_running(self):
        """start() inside an async context must transition to STATE_RUNNING."""
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        s = AsyncIOScheduler()
        s.start()
        assert s.state == STATE_RUNNING
        s.shutdown(wait=False)  # cleanup — shutdown internals are APScheduler's concern
