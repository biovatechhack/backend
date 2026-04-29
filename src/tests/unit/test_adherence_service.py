"""Unit tests for the Adherence (check-adherence) feature.

Covers:
- AdherenceIn DTO validation (blank fields, invalid meal_context)
- AdherenceService.confirm_dose: medication matching, log fields, PatientNotFoundError
- AdherenceService.get_history: pct calculation, rounding, empty history
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from application.services.adherence_service import AdherenceService
from domain.entities.medication_log import MedicationLog
from domain.entities.medication_schedule import MedicationSchedule
from domain.exceptions import PatientNotFoundError
from presentation.api.dtos.adherence_dtos import AdherenceIn

# ── Shared helpers ────────────────────────────────────────────────────────────

PATIENT_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"


def _make_schedule(medication: str = "Metformin 500mg", scheduled_time: str = "08:00") -> MedicationSchedule:
    return MedicationSchedule(
        patient_id=PATIENT_ID,
        medication=medication,
        scheduled_time=scheduled_time,
        frequency="daily",
        meal_context="after",
    )


def _make_log(taken: bool, medication: str = "Metformin 500mg") -> MedicationLog:
    now = datetime.now(UTC)
    return MedicationLog(
        id="log-001",
        patient_id=PATIENT_ID,
        medication=medication,
        scheduled_at=now,
        taken=taken,
        meal_context="after",
        confirmed_at=now,
    )


def _make_repos(schedules: list, logs: list):
    schedule_repo = MagicMock()
    schedule_repo.get_active_by_patient = AsyncMock(return_value=schedules)

    log_repo = MagicMock()
    log_repo.save = AsyncMock(return_value="log-001")
    log_repo.get_by_patient_since = AsyncMock(return_value=logs)
    return schedule_repo, log_repo


# ── AdherenceIn DTO validation ────────────────────────────────────────────────


class TestAdherenceIn:
    def test_valid_payload_accepted(self):
        dto = AdherenceIn(
            patient_id=PATIENT_ID,
            medication="Metformin 500mg",
            taken=True,
            meal_context="after",
        )
        assert dto.taken is True

    def test_blank_patient_id_raises(self):
        with pytest.raises(ValueError, match="blank"):
            AdherenceIn(
                patient_id="   ",
                medication="Metformin 500mg",
                taken=True,
                meal_context="after",
            )

    def test_blank_medication_raises(self):
        with pytest.raises(ValueError, match="blank"):
            AdherenceIn(
                patient_id=PATIENT_ID,
                medication="",
                taken=True,
                meal_context="before",
            )

    def test_whitespace_stripped_from_fields(self):
        """Leading/trailing whitespace must be normalised before storage."""
        dto = AdherenceIn(
            patient_id=f"  {PATIENT_ID}  ",
            medication="  Metformin 500mg  ",
            taken=False,
            meal_context="with",
        )
        assert dto.patient_id == PATIENT_ID
        assert dto.medication == "Metformin 500mg"

    def test_invalid_meal_context_raises(self):
        with pytest.raises(ValueError):
            AdherenceIn(
                patient_id=PATIENT_ID,
                medication="Metformin 500mg",
                taken=True,
                meal_context="during",   # not in Literal
            )

    def test_all_valid_meal_contexts_accepted(self):
        for ctx in ("before", "after", "with"):
            dto = AdherenceIn(
                patient_id=PATIENT_ID,
                medication="X",
                taken=True,
                meal_context=ctx,
            )
            assert dto.meal_context == ctx


# ── AdherenceService.confirm_dose ────────────────────────────────────────────


class TestConfirmDose:
    async def test_raises_when_no_active_schedules(self):
        """A patient with no schedule cannot confirm a dose."""
        schedule_repo, log_repo = _make_repos(schedules=[], logs=[])
        svc = AdherenceService(schedule_repo, log_repo)
        with pytest.raises(PatientNotFoundError):
            await svc.confirm_dose(PATIENT_ID, "Metformin 500mg", taken=True, meal_context="after")

    async def test_log_saved_to_repository(self):
        s = _make_schedule()
        schedule_repo, log_repo = _make_repos(schedules=[s], logs=[])
        svc = AdherenceService(schedule_repo, log_repo)
        await svc.confirm_dose(PATIENT_ID, "Metformin 500mg", taken=True, meal_context="after")
        log_repo.save.assert_called_once()

    async def test_returned_log_has_correct_patient_and_medication(self):
        s = _make_schedule()
        schedule_repo, log_repo = _make_repos(schedules=[s], logs=[])
        svc = AdherenceService(schedule_repo, log_repo)
        log = await svc.confirm_dose(PATIENT_ID, "Metformin 500mg", taken=True, meal_context="after")
        assert log.patient_id == PATIENT_ID
        assert log.medication == "Metformin 500mg"

    async def test_taken_flag_preserved_in_log(self):
        s = _make_schedule()
        schedule_repo, log_repo = _make_repos(schedules=[s], logs=[])
        svc = AdherenceService(schedule_repo, log_repo)
        log = await svc.confirm_dose(PATIENT_ID, "Metformin 500mg", taken=False, meal_context="after")
        assert log.taken is False

    async def test_meal_context_preserved_in_log(self):
        s = _make_schedule()
        schedule_repo, log_repo = _make_repos(schedules=[s], logs=[])
        svc = AdherenceService(schedule_repo, log_repo)
        log = await svc.confirm_dose(PATIENT_ID, "Metformin 500mg", taken=True, meal_context="before")
        assert log.meal_context == "before"

    async def test_exact_medication_match_is_used_for_schedule_time(self):
        """When two schedules exist, the one matching the input medication is used."""
        s1 = _make_schedule(medication="Glipizide 5mg", scheduled_time="07:00")
        s2 = _make_schedule(medication="Metformin 500mg", scheduled_time="08:30")
        schedule_repo, log_repo = _make_repos(schedules=[s1, s2], logs=[])
        svc = AdherenceService(schedule_repo, log_repo)
        log = await svc.confirm_dose(PATIENT_ID, "Metformin 500mg", taken=True, meal_context="after")
        assert log.scheduled_at.hour == 8
        assert log.scheduled_at.minute == 30

    async def test_case_insensitive_medication_matching(self):
        """Medication name comparison must be case-insensitive (user input varies)."""
        s = _make_schedule(medication="Metformin 500mg")
        schedule_repo, log_repo = _make_repos(schedules=[s], logs=[])
        svc = AdherenceService(schedule_repo, log_repo)
        log = await svc.confirm_dose(PATIENT_ID, "metformin 500mg", taken=True, meal_context="after")
        assert log.medication == "metformin 500mg"

    async def test_no_exact_match_falls_back_to_first_schedule(self):
        """Unknown medication still gets logged — uses first schedule for timing."""
        s = _make_schedule(medication="Metformin 500mg", scheduled_time="08:00")
        schedule_repo, log_repo = _make_repos(schedules=[s], logs=[])
        svc = AdherenceService(schedule_repo, log_repo)
        log = await svc.confirm_dose(PATIENT_ID, "OtherDrug", taken=True, meal_context="after")
        assert log.scheduled_at.hour == 8

    async def test_log_has_confirmed_at_timestamp(self):
        s = _make_schedule()
        schedule_repo, log_repo = _make_repos(schedules=[s], logs=[])
        svc = AdherenceService(schedule_repo, log_repo)
        log = await svc.confirm_dose(PATIENT_ID, "Metformin 500mg", taken=True, meal_context="after")
        assert log.confirmed_at is not None


# ── AdherenceService.get_history ──────────────────────────────────────────────


class TestGetHistory:
    async def test_empty_logs_returns_zero_pct(self):
        """Avoid ZeroDivisionError when a patient has no records."""
        schedule_repo, log_repo = _make_repos(schedules=[], logs=[])
        svc = AdherenceService(schedule_repo, log_repo)
        history = await svc.get_history(PATIENT_ID, days=7)
        assert history.adherence_pct == 0.0
        assert history.total_scheduled == 0
        assert history.total_taken == 0

    async def test_all_taken_returns_100_pct(self):
        logs = [_make_log(taken=True) for _ in range(5)]
        schedule_repo, log_repo = _make_repos(schedules=[], logs=logs)
        svc = AdherenceService(schedule_repo, log_repo)
        history = await svc.get_history(PATIENT_ID, days=7)
        assert history.adherence_pct == 100.0

    async def test_none_taken_returns_0_pct(self):
        logs = [_make_log(taken=False) for _ in range(3)]
        schedule_repo, log_repo = _make_repos(schedules=[], logs=logs)
        svc = AdherenceService(schedule_repo, log_repo)
        history = await svc.get_history(PATIENT_ID, days=7)
        assert history.adherence_pct == 0.0

    async def test_partial_adherence_rounds_to_one_decimal(self):
        """2 taken out of 3 = 66.7% (not 66.66...)."""
        logs = [_make_log(taken=True), _make_log(taken=True), _make_log(taken=False)]
        schedule_repo, log_repo = _make_repos(schedules=[], logs=logs)
        svc = AdherenceService(schedule_repo, log_repo)
        history = await svc.get_history(PATIENT_ID, days=7)
        assert history.adherence_pct == 66.7

    async def test_one_in_three_rounds_to_one_decimal(self):
        """1 taken out of 3 = 33.3% (not 33.33...)."""
        logs = [_make_log(taken=True), _make_log(taken=False), _make_log(taken=False)]
        schedule_repo, log_repo = _make_repos(schedules=[], logs=logs)
        svc = AdherenceService(schedule_repo, log_repo)
        history = await svc.get_history(PATIENT_ID, days=7)
        assert history.adherence_pct == 33.3

    async def test_counts_match_log_list(self):
        logs = [_make_log(taken=True), _make_log(taken=False), _make_log(taken=True)]
        schedule_repo, log_repo = _make_repos(schedules=[], logs=logs)
        svc = AdherenceService(schedule_repo, log_repo)
        history = await svc.get_history(PATIENT_ID, days=7)
        assert history.total_scheduled == 3
        assert history.total_taken == 2

    async def test_logs_list_returned_unchanged(self):
        logs = [_make_log(taken=True)]
        schedule_repo, log_repo = _make_repos(schedules=[], logs=logs)
        svc = AdherenceService(schedule_repo, log_repo)
        history = await svc.get_history(PATIENT_ID, days=7)
        assert history.logs == logs

    async def test_repo_called_with_correct_since_window(self):
        """The `since` cutoff must be approximately `now - days`."""
        schedule_repo, log_repo = _make_repos(schedules=[], logs=[])
        svc = AdherenceService(schedule_repo, log_repo)
        before = datetime.now(UTC)
        await svc.get_history(PATIENT_ID, days=14)
        after = datetime.now(UTC)

        _, call_kwargs = log_repo.get_by_patient_since.call_args
        since = log_repo.get_by_patient_since.call_args[0][1]

        expected_low = before - timedelta(days=14, seconds=1)
        expected_high = after - timedelta(days=14) + timedelta(seconds=1)
        assert expected_low <= since <= expected_high
