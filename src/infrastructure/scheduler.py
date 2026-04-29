from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from abstraction.repositories.medication_schedule_repository_port import (
    MedicationScheduleRepositoryPort,
)
from domain.entities.medication_schedule import MedicationSchedule
from infrastructure.notifications.reminder_email import send_push_reminder

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Night-quiet window: no reminders sent between 22:00 and 08:00 (inclusive start).
_QUIET_START = 22
_QUIET_END = 8


def _in_quiet_window() -> bool:
    hour = datetime.now().hour
    return hour >= _QUIET_START or hour < _QUIET_END


async def _reminder_job(
    schedule_id: str, patient_id: str, medication: str, meal_context: str
) -> None:
    if _in_quiet_window():
        logger.info(
            "reminder suppressed (quiet window) schedule_id=%s patient=%s",
            schedule_id,
            patient_id,
        )
        return

    await send_push_reminder(patient_id, medication, meal_context)


def _job_ids(schedule: MedicationSchedule) -> list[tuple[str, int, int]]:
    """Return (job_id, hour, minute) tuples for a schedule.

    twice_daily fires a second dose 12 hours after the primary time.
    """
    h, m = map(int, schedule.scheduled_time.split(":"))
    entries = [(schedule.id, h, m)]
    if schedule.frequency == "twice_daily":
        entries.append((f"{schedule.id}_2", (h + 12) % 24, m))
    return entries


def register_reminder(schedule: MedicationSchedule) -> None:
    """Add APScheduler cron job(s) for the given schedule."""
    for job_id, hour, minute in _job_ids(schedule):
        scheduler.add_job(
            _reminder_job,
            trigger="cron",
            hour=hour,
            minute=minute,
            id=job_id,
            replace_existing=True,
            kwargs={
                "schedule_id": schedule.id,
                "patient_id": schedule.patient_id,
                "medication": schedule.medication,
                "meal_context": schedule.meal_context,
            },
        )
        logger.info("scheduler.register job_id=%s at %02d:%02d", job_id, hour, minute)


def unregister_reminder(schedule_id: str) -> None:
    """Remove APScheduler job(s) for a schedule. Silent if jobs don't exist."""
    for job_id in (schedule_id, f"{schedule_id}_2"):
        job = scheduler.get_job(job_id)
        if job:
            job.remove()
            logger.info("scheduler.unregister job_id=%s", job_id)


async def reload_from_db(repo: MedicationScheduleRepositoryPort) -> int:
    """Re-register all active schedules from persistent storage.

    Called once at startup so jobs survive a server restart.
    Returns the number of schedules reloaded.
    """
    schedules = await repo.get_all_active()
    for schedule in schedules:
        register_reminder(schedule)
    logger.info("scheduler.reload count=%d", len(schedules))
    return len(schedules)
