"""Integration tests for the FastAPI lifespan context manager.

Covers:
- Scheduler is RUNNING while the app is live (lifespan started it)
- Scheduler is STOPPED after the app shuts down (lifespan shut it down)
- App still responds to requests during lifespan (regression guard)
- Health endpoint returns 200 after lifespan startup
"""
from apscheduler.schedulers.base import STATE_RUNNING, STATE_STOPPED
from fastapi.testclient import TestClient


class TestLifespan:
    def test_scheduler_is_running_during_app_lifetime(self):
        """scheduler.state must be RUNNING inside the TestClient context."""
        from infrastructure.scheduler import scheduler
        from presentation.api.main import app

        with TestClient(app):
            assert scheduler.state == STATE_RUNNING

    def test_scheduler_is_stopped_after_app_exits(self):
        """scheduler.state must be STOPPED once the TestClient context exits."""
        from infrastructure.scheduler import scheduler
        from presentation.api.main import app

        with TestClient(app):
            pass  # lifespan runs fully

        assert scheduler.state == STATE_STOPPED

    def test_health_endpoint_reachable_during_lifespan(self):
        """App must respond to requests after lifespan startup completes."""
        from presentation.api.main import app

        with TestClient(app) as client:
            response = client.get("/api/v1/health")
            assert response.status_code == 200

    def test_multiple_lifespan_cycles_do_not_break_scheduler(self):
        """start/stop/start/stop must not raise — scheduler is reusable."""
        from infrastructure.scheduler import scheduler
        from presentation.api.main import app

        for _ in range(2):
            with TestClient(app):
                assert scheduler.state == STATE_RUNNING
            assert scheduler.state == STATE_STOPPED
