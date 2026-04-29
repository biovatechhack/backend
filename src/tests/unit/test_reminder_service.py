"""Unit tests for the Reminder CRUD feature.

Covers:
- ReminderCreate / ReminderPatch Pydantic validation
- ReminderService.create / list_active / update / deactivate
- infrastructure/scheduler helpers: _job_ids, _in_quiet_window,
  register_reminder, unregister_reminder
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from application.services.reminder_service import ReminderService
from domain.entities.medication_schedule import MedicationSchedule
from domain.models.reminder_models import ReminderCreate, ReminderPatch

# ── Shared test data ──────────────────────────────────────────────────────────

PATIENT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
SCHEDULE_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def _make_schedule(
    *,
    frequency: str = "daily",
    scheduled_time: str = "08:00",
    schedule_id: str = SCHEDULE_ID,
) -> MedicationSchedule:
    s = MedicationSchedule(
        patient_id=PATIENT_ID,
        medication="Metformin 500mg",
        scheduled_time=scheduled_time,
        frequency=frequency,
        meal_context="after",
    )
    s.id = schedule_id
    return s


def _make_repo(schedule: MedicationSchedule | None = None) -> MagicMock:
    repo = MagicMock()
    repo.save = AsyncMock(return_value=SCHEDULE_ID)
    repo.get_by_id = AsyncMock(return_value=schedule)
    repo.get_active_by_patient = AsyncMock(
        return_value=[schedule] if schedule else []
    )
    repo.update = AsyncMock()
    repo.set_active = AsyncMock()
    return repo


# ── ReminderCreate validation ─────────────────────────────────────────────────


class TestReminderCreate:
    def test_valid_payload_is_accepted(self):
        m = ReminderCreate(
            patient_id=PATIENT_ID,
            medication="Metformin 500mg",
            scheduled_time="08:00",
            frequency="daily",
            meal_context="after",
        )
        assert m.scheduled_time == "08:00"
        assert m.frequency == "daily"

    def test_invalid_time_format_raises(self):
        """Scheduler would silently fire at wrong hour without this guard."""
        with pytest.raises(ValueError, match="HH:MM"):
            ReminderCreate(
                patient_id=PATIENT_ID,
                medication="X",
                scheduled_time="8:00",   # missing leading zero
                frequency="daily",
                meal_context="before",
            )

    def test_non_numeric_time_raises(self):
        with pytest.raises(ValueError):
            ReminderCreate(
                patient_id=PATIENT_ID,
                medication="X",
                scheduled_time="AA:BB",
                frequency="daily",
                meal_context="before",
            )

    def test_invalid_frequency_raises(self):
        with pytest.raises(ValueError):
            ReminderCreate(
                patient_id=PATIENT_ID,
                medication="X",
                scheduled_time="08:00",
                frequency="weekly",   # not in Literal
                meal_context="after",
            )

    def test_invalid_meal_context_raises(self):
        with pytest.raises(ValueError):
            ReminderCreate(
                patient_id=PATIENT_ID,
                medication="X",
                scheduled_time="08:00",
                frequency="daily",
                meal_context="during",   # not in Literal
            )

    def test_boundary_time_2359_is_valid(self):
        m = ReminderCreate(
            patient_id=PATIENT_ID,
            medication="X",
            scheduled_time="23:59",
            frequency="twice_daily",
            meal_context="before",
        )
        assert m.scheduled_time == "23:59"

    def test_time_2400_is_invalid(self):
        with pytest.raises(ValueError):
            ReminderCreate(
                patient_id=PATIENT_ID,
                medication="X",
                scheduled_time="24:00",
                frequency="daily",
                meal_context="before",
            )


# ── ReminderPatch validation ──────────────────────────────────────────────────


class TestReminderPatch:
    def test_empty_patch_is_valid(self):
        """A PATCH with no fields is a no-op — must not raise."""
        p = ReminderPatch()
        assert p.scheduled_time is None
        assert p.frequency is None

    def test_valid_time_patch(self):
        p = ReminderPatch(scheduled_time="14:30")
        assert p.scheduled_time == "14:30"

    def test_invalid_time_patch_raises(self):
        with pytest.raises(ValueError):
            ReminderPatch(scheduled_time="9:5")

    def test_valid_frequency_patch(self):
        p = ReminderPatch(frequency="twice_daily")
        assert p.frequency == "twice_daily"


# ── ReminderService.create ────────────────────────────────────────────────────


class TestReminderServiceCreate:
    async def test_saves_to_repo(self):
        repo = _make_repo()
        with patch("application.services.reminder_service.register_reminder"):
            svc = ReminderService(repo=repo)
            data = ReminderCreate(
                patient_id=PATIENT_ID,
                medication="Metformin 500mg",
                scheduled_time="08:00",
                frequency="daily",
                meal_context="after",
            )
            await svc.create(data)
        repo.save.assert_called_once()

    async def test_registers_reminder_in_scheduler(self):
        repo = _make_repo()
        with patch("application.services.reminder_service.register_reminder") as mock_reg:
            svc = ReminderService(repo=repo)
            data = ReminderCreate(
                patient_id=PATIENT_ID,
                medication="Metformin 500mg",
                scheduled_time="08:00",
                frequency="daily",
                meal_context="after",
            )
            schedule = await svc.create(data)
        mock_reg.assert_called_once_with(schedule)

    async def test_returned_schedule_has_correct_fields(self):
        repo = _make_repo()
        with patch("application.services.reminder_service.register_reminder"):
            svc = ReminderService(repo=repo)
            data = ReminderCreate(
                patient_id=PATIENT_ID,
                medication="Metformin 500mg",
                scheduled_time="08:00",
                frequency="daily",
                meal_context="after",
            )
            schedule = await svc.create(data)
        assert schedule.patient_id == PATIENT_ID
        assert schedule.medication == "Metformin 500mg"
        assert schedule.scheduled_time == "08:00"
        assert schedule.active is True


# ── ReminderService.list_active ───────────────────────────────────────────────


class TestReminderServiceListActive:
    async def test_delegates_to_repo(self):
        s = _make_schedule()
        repo = _make_repo(s)
        svc = ReminderService(repo=repo)
        result = await svc.list_active(PATIENT_ID)
        repo.get_active_by_patient.assert_called_once_with(PATIENT_ID)
        assert result == [s]

    async def test_returns_empty_list_when_no_schedules(self):
        repo = _make_repo()
        svc = ReminderService(repo=repo)
        result = await svc.list_active(PATIENT_ID)
        assert result == []


# ── ReminderService.update ────────────────────────────────────────────────────


class TestReminderServiceUpdate:
    async def test_patches_scheduled_time(self):
        s = _make_schedule()
        repo = _make_repo(s)
        with patch("application.services.reminder_service.register_reminder"), \
             patch("application.services.reminder_service.unregister_reminder"):
            svc = ReminderService(repo=repo)
            result = await svc.update(SCHEDULE_ID, ReminderPatch(scheduled_time="14:00"))
        assert result is not None
        assert result.scheduled_time == "14:00"

    async def test_patches_frequency(self):
        s = _make_schedule()
        repo = _make_repo(s)
        with patch("application.services.reminder_service.register_reminder"), \
             patch("application.services.reminder_service.unregister_reminder"):
            svc = ReminderService(repo=repo)
            result = await svc.update(SCHEDULE_ID, ReminderPatch(frequency="twice_daily"))
        assert result is not None
        assert result.frequency == "twice_daily"

    async def test_unregisters_old_job_then_registers_new(self):
        s = _make_schedule()
        repo = _make_repo(s)
        with patch("application.services.reminder_service.register_reminder") as mock_reg, \
             patch("application.services.reminder_service.unregister_reminder") as mock_unreg:
            svc = ReminderService(repo=repo)
            await svc.update(SCHEDULE_ID, ReminderPatch(scheduled_time="14:00"))
        mock_unreg.assert_called_once_with(SCHEDULE_ID)
        mock_reg.assert_called_once()

    async def test_returns_none_when_schedule_not_found(self):
        repo = _make_repo(schedule=None)
        svc = ReminderService(repo=repo)
        result = await svc.update("nonexistent", ReminderPatch(scheduled_time="14:00"))
        assert result is None

    async def test_repo_update_called_with_modified_schedule(self):
        s = _make_schedule()
        repo = _make_repo(s)
        with patch("application.services.reminder_service.register_reminder"), \
             patch("application.services.reminder_service.unregister_reminder"):
            svc = ReminderService(repo=repo)
            await svc.update(SCHEDULE_ID, ReminderPatch(scheduled_time="14:00"))
        repo.update.assert_called_once()


# ── ReminderService.deactivate ────────────────────────────────────────────────


class TestReminderServiceDeactivate:
    async def test_calls_set_active_false(self):
        s = _make_schedule()
        repo = _make_repo(s)
        with patch("application.services.reminder_service.unregister_reminder"):
            svc = ReminderService(repo=repo)
            await svc.deactivate(SCHEDULE_ID)
        repo.set_active.assert_called_once_with(SCHEDULE_ID, active=False)

    async def test_unregisters_scheduler_job(self):
        s = _make_schedule()
        repo = _make_repo(s)
        with patch("application.services.reminder_service.unregister_reminder") as mock_unreg:
            svc = ReminderService(repo=repo)
            await svc.deactivate(SCHEDULE_ID)
        mock_unreg.assert_called_once_with(SCHEDULE_ID)

    async def test_returns_true_when_schedule_found(self):
        s = _make_schedule()
        repo = _make_repo(s)
        with patch("application.services.reminder_service.unregister_reminder"):
            svc = ReminderService(repo=repo)
            result = await svc.deactivate(SCHEDULE_ID)
        assert result is True

    async def test_returns_false_when_schedule_not_found(self):
        repo = _make_repo(schedule=None)
        svc = ReminderService(repo=repo)
        result = await svc.deactivate("nonexistent")
        assert result is False


# ── Scheduler: _job_ids ───────────────────────────────────────────────────────


class TestJobIds:
    """_job_ids drives how many cron jobs are created per schedule."""

    def test_daily_produces_one_entry(self):
        from infrastructure.scheduler import _job_ids
        s = _make_schedule(frequency="daily", scheduled_time="08:00")
        jobs = _job_ids(s)
        assert len(jobs) == 1
        assert jobs[0][1] == 8   # hour
        assert jobs[0][2] == 0   # minute

    def test_twice_daily_produces_two_entries(self):
        from infrastructure.scheduler import _job_ids
        s = _make_schedule(frequency="twice_daily", scheduled_time="08:00")
        jobs = _job_ids(s)
        assert len(jobs) == 2

    def test_twice_daily_second_job_is_12h_later(self):
        from infrastructure.scheduler import _job_ids
        s = _make_schedule(frequency="twice_daily", scheduled_time="08:00")
        jobs = _job_ids(s)
        assert jobs[1][1] == 20   # 08 + 12
        assert jobs[1][2] == 0

    def test_twice_daily_wraps_past_midnight(self):
        """14:30 + 12h = 02:30 (not 26:30)."""
        from infrastructure.scheduler import _job_ids
        s = _make_schedule(frequency="twice_daily", scheduled_time="14:30")
        jobs = _job_ids(s)
        assert jobs[1][1] == 2
        assert jobs[1][2] == 30

    def test_twice_daily_second_job_id_has_suffix(self):
        from infrastructure.scheduler import _job_ids
        s = _make_schedule(frequency="twice_daily", schedule_id="s1")
        jobs = _job_ids(s)
        assert jobs[1][0] == "s1_2"

    def test_daily_job_id_has_no_suffix(self):
        from infrastructure.scheduler import _job_ids
        s = _make_schedule(frequency="daily", schedule_id="s1")
        jobs = _job_ids(s)
        assert jobs[0][0] == "s1"


# ── Scheduler: _in_quiet_window ───────────────────────────────────────────────


class TestQuietWindow:
    """Night-quiet guard: no reminders between 22:00–07:59 inclusive."""

    def _mock_hour(self, hour: int):
        dt = MagicMock()
        dt.hour = hour
        return dt

    def test_quiet_at_22(self):
        from infrastructure.scheduler import _in_quiet_window
        with patch("infrastructure.scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = self._mock_hour(22)
            assert _in_quiet_window() is True

    def test_quiet_at_midnight(self):
        from infrastructure.scheduler import _in_quiet_window
        with patch("infrastructure.scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = self._mock_hour(0)
            assert _in_quiet_window() is True

    def test_quiet_at_7(self):
        from infrastructure.scheduler import _in_quiet_window
        with patch("infrastructure.scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = self._mock_hour(7)
            assert _in_quiet_window() is True

    def test_not_quiet_at_8(self):
        """08:00 is the first allowed hour — the boundary must be exclusive."""
        from infrastructure.scheduler import _in_quiet_window
        with patch("infrastructure.scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = self._mock_hour(8)
            assert _in_quiet_window() is False

    def test_not_quiet_at_noon(self):
        from infrastructure.scheduler import _in_quiet_window
        with patch("infrastructure.scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = self._mock_hour(12)
            assert _in_quiet_window() is False

    def test_not_quiet_at_21(self):
        """21:00 is still within the allowed window — one hour before quiet."""
        from infrastructure.scheduler import _in_quiet_window
        with patch("infrastructure.scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = self._mock_hour(21)
            assert _in_quiet_window() is False


# ── Scheduler: register_reminder / unregister_reminder ───────────────────────


class TestRegisterReminder:
    def test_daily_adds_one_job(self):
        from infrastructure.scheduler import register_reminder
        s = _make_schedule(frequency="daily")
        with patch("infrastructure.scheduler.scheduler") as mock_sched:
            register_reminder(s)
        assert mock_sched.add_job.call_count == 1

    def test_twice_daily_adds_two_jobs(self):
        from infrastructure.scheduler import register_reminder
        s = _make_schedule(frequency="twice_daily")
        with patch("infrastructure.scheduler.scheduler") as mock_sched:
            register_reminder(s)
        assert mock_sched.add_job.call_count == 2

    def test_replace_existing_is_true(self):
        """Duplicate job IDs must overwrite, not raise."""
        from infrastructure.scheduler import register_reminder
        s = _make_schedule(frequency="daily")
        with patch("infrastructure.scheduler.scheduler") as mock_sched:
            register_reminder(s)
        kwargs = mock_sched.add_job.call_args[1]
        assert kwargs["replace_existing"] is True

    def test_job_trigger_is_cron(self):
        from infrastructure.scheduler import register_reminder
        s = _make_schedule(frequency="daily")
        with patch("infrastructure.scheduler.scheduler") as mock_sched:
            register_reminder(s)
        args = mock_sched.add_job.call_args[1]
        assert args["trigger"] == "cron"

    def test_correct_hour_and_minute_passed(self):
        from infrastructure.scheduler import register_reminder
        s = _make_schedule(frequency="daily", scheduled_time="14:30")
        with patch("infrastructure.scheduler.scheduler") as mock_sched:
            register_reminder(s)
        kwargs = mock_sched.add_job.call_args[1]
        assert kwargs["hour"] == 14
        assert kwargs["minute"] == 30


class TestUnregisterReminder:
    def test_removes_existing_job(self):
        from infrastructure.scheduler import unregister_reminder
        mock_job = MagicMock()
        with patch("infrastructure.scheduler.scheduler") as mock_sched:
            mock_sched.get_job.side_effect = lambda jid: mock_job if jid == "s1" else None
            unregister_reminder("s1")
        mock_job.remove.assert_called_once()

    def test_silent_when_job_not_found(self):
        """Missing job IDs must not raise — unregister is idempotent."""
        from infrastructure.scheduler import unregister_reminder
        with patch("infrastructure.scheduler.scheduler") as mock_sched:
            mock_sched.get_job.return_value = None
            unregister_reminder("nonexistent")   # must not raise

    def test_twice_daily_removes_both_jobs(self):
        """A twice_daily schedule creates two jobs; both must be cleaned up."""
        from infrastructure.scheduler import unregister_reminder
        mock_job = MagicMock()
        with patch("infrastructure.scheduler.scheduler") as mock_sched:
            mock_sched.get_job.return_value = mock_job
            unregister_reminder("s1")
        assert mock_job.remove.call_count == 2
