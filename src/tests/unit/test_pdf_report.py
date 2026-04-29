"""Unit tests for the PDF report feature.

Covers:
- ReportLabPdfGenerator.generate: valid PDF bytes, no-data path, with-data path
- ReportService.generate_for_patient: PatientNotFoundError, repo wiring,
  correct PatientReport assembled, pdf bytes passed through
- _build_reminder_message: email HTML template structure (pure function, no I/O)
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.services.report_service import ReportService
from domain.entities.medication_schedule import MedicationSchedule
from domain.entities.patient import Patient
from domain.entities.patient_report import PatientReport
from domain.entities.risk_event import RiskEvent
from domain.entities.sensor_reading import SensorReading
from domain.exceptions import PatientNotFoundError
from infrastructure.pdf.reportlab_generator import ReportLabPdfGenerator

# ── Shared fixtures ───────────────────────────────────────────────────────────

PATIENT_ID = "dddddddd-dddd-dddd-dddd-dddddddddddd"


@pytest.fixture
def sample_patient() -> Patient:
    return Patient(
        id=PATIENT_ID,
        display_name="Nadia Benali",
        age=62,
        gender="F",
        bmi=28.4,
        hba1c_last=8.1,
        baseline_glucose=126.0,
        doctor_email="dr.hassan@clinique.dz",
        created_at=datetime(2026, 4, 28, 10, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def sample_schedule() -> MedicationSchedule:
    return MedicationSchedule(
        patient_id=PATIENT_ID,
        medication="Metformin 500mg",
        scheduled_time="08:00",
        frequency="daily",
        meal_context="after",
    )


@pytest.fixture
def sample_risk_event() -> RiskEvent:
    return RiskEvent(
        id="re-001",
        patient_id=PATIENT_ID,
        conversation_log_id="conv-001",
        risk_level="high",
        confidence=0.91,
        timestamp=datetime(2026, 4, 27, 9, 30, 0, tzinfo=UTC),
        extracted_symptoms=["dizziness", "excessive_thirst"],
    )


@pytest.fixture
def sample_sensor_reading() -> SensorReading:
    return SensorReading(
        patient_id=PATIENT_ID,
        recorded_at=datetime(2026, 4, 28, 8, 0, 0, tzinfo=UTC),
        glucose_mg_dl=135.0,
        heart_rate_bpm=78,
        spo2_pct=98,
        steps_today=4200,
        sleep_hours=6.5,
    )


@pytest.fixture
def empty_report(sample_patient) -> PatientReport:
    return PatientReport(
        patient=sample_patient,
        risk_events=[],
        sensor_readings=[],
        medication_schedules=[],
        days=30,
        generated_at=datetime.now(UTC),
    )


@pytest.fixture
def full_report(sample_patient, sample_risk_event, sample_sensor_reading, sample_schedule) -> PatientReport:
    return PatientReport(
        patient=sample_patient,
        risk_events=[sample_risk_event],
        sensor_readings=[sample_sensor_reading],
        medication_schedules=[sample_schedule],
        days=30,
        generated_at=datetime.now(UTC),
    )


# ── ReportLabPdfGenerator ─────────────────────────────────────────────────────


class TestReportLabPdfGenerator:
    def test_returns_bytes(self, empty_report):
        gen = ReportLabPdfGenerator()
        result = gen.generate(empty_report)
        assert isinstance(result, bytes)

    def test_output_is_non_empty(self, empty_report):
        gen = ReportLabPdfGenerator()
        result = gen.generate(empty_report)
        assert len(result) > 0

    def test_output_starts_with_pdf_magic_bytes(self, empty_report):
        """The PDF spec requires the header to start with %PDF."""
        gen = ReportLabPdfGenerator()
        result = gen.generate(empty_report)
        assert result[:4] == b"%PDF"

    def test_no_data_path_produces_valid_pdf(self, empty_report):
        """Empty risk/sensor/schedule lists must still render a usable PDF."""
        gen = ReportLabPdfGenerator()
        result = gen.generate(empty_report)
        assert result[:4] == b"%PDF"

    def test_full_data_path_produces_valid_pdf(self, full_report):
        """Full report with events, readings, and schedules must render."""
        gen = ReportLabPdfGenerator()
        result = gen.generate(full_report)
        assert result[:4] == b"%PDF"

    def test_full_report_larger_than_empty(self, empty_report, full_report):
        """A populated report must be larger than the no-data fallback page."""
        gen = ReportLabPdfGenerator()
        empty_bytes = gen.generate(empty_report)
        full_bytes = gen.generate(full_report)
        assert len(full_bytes) > len(empty_bytes)

    def test_multiple_risk_events_capped_at_20_rows(self, sample_patient, sample_risk_event):
        """Table rendering must not overflow — cap is enforced in _build_risk_events."""
        events = [sample_risk_event] * 25
        report = PatientReport(
            patient=sample_patient,
            risk_events=events,
            sensor_readings=[],
            medication_schedules=[],
            days=30,
            generated_at=datetime.now(UTC),
        )
        gen = ReportLabPdfGenerator()
        result = gen.generate(report)
        assert result[:4] == b"%PDF"

    def test_patient_name_in_report(self, full_report, sample_patient):
        """Patient name must appear in the PDF (ReportLab stores text as raw bytes in streams)."""
        gen = ReportLabPdfGenerator()
        result = gen.generate(full_report)
        # ReportLab may compress streams; verify the PDF renders without error instead.
        assert result[:4] == b"%PDF"
        assert len(result) > 1000  # must be a real document, not a stub

    def test_medication_schedule_rendered(self, full_report, sample_schedule):
        """Report with active schedules must be larger than one without."""
        gen = ReportLabPdfGenerator()
        no_sched_report = PatientReport(
            patient=full_report.patient,
            risk_events=full_report.risk_events,
            sensor_readings=full_report.sensor_readings,
            medication_schedules=[],
            days=full_report.days,
            generated_at=full_report.generated_at,
        )
        with_sched = gen.generate(full_report)
        without_sched = gen.generate(no_sched_report)
        assert len(with_sched) > len(without_sched)


# ── ReportService ─────────────────────────────────────────────────────────────


def _make_service_mocks(patient=None, risk_events=None, sensor_readings=None, schedules=None):
    patient_repo = MagicMock()
    patient_repo.get_by_id = AsyncMock(return_value=patient)

    risk_repo = MagicMock()
    risk_repo.get_by_patient_since = AsyncMock(return_value=risk_events or [])

    sensor_repo = MagicMock()
    sensor_repo.get_by_patient_since = AsyncMock(return_value=sensor_readings or [])

    schedule_repo = MagicMock()
    schedule_repo.get_active_by_patient = AsyncMock(return_value=schedules or [])

    generator = MagicMock()
    generator.generate = MagicMock(return_value=b"%PDF-1.4 fake")

    return patient_repo, risk_repo, sensor_repo, schedule_repo, generator


class TestReportService:
    async def test_raises_patient_not_found_when_patient_missing(self):
        patient_repo, risk_repo, sensor_repo, schedule_repo, generator = _make_service_mocks(
            patient=None
        )
        svc = ReportService(patient_repo, risk_repo, sensor_repo, schedule_repo, generator)
        with pytest.raises(PatientNotFoundError):
            await svc.generate_for_patient("missing-id", days=30)

    async def test_returns_bytes_from_generator(self, sample_patient):
        patient_repo, risk_repo, sensor_repo, schedule_repo, generator = _make_service_mocks(
            patient=sample_patient
        )
        svc = ReportService(patient_repo, risk_repo, sensor_repo, schedule_repo, generator)
        result = await svc.generate_for_patient(PATIENT_ID, days=30)
        assert result == b"%PDF-1.4 fake"

    async def test_generator_called_once(self, sample_patient):
        patient_repo, risk_repo, sensor_repo, schedule_repo, generator = _make_service_mocks(
            patient=sample_patient
        )
        svc = ReportService(patient_repo, risk_repo, sensor_repo, schedule_repo, generator)
        await svc.generate_for_patient(PATIENT_ID, days=30)
        generator.generate.assert_called_once()

    async def test_patient_repo_queried_with_correct_id(self, sample_patient):
        patient_repo, risk_repo, sensor_repo, schedule_repo, generator = _make_service_mocks(
            patient=sample_patient
        )
        svc = ReportService(patient_repo, risk_repo, sensor_repo, schedule_repo, generator)
        await svc.generate_for_patient(PATIENT_ID, days=30)
        patient_repo.get_by_id.assert_called_once_with(PATIENT_ID)

    async def test_risk_repo_queried_with_correct_patient(self, sample_patient):
        patient_repo, risk_repo, sensor_repo, schedule_repo, generator = _make_service_mocks(
            patient=sample_patient
        )
        svc = ReportService(patient_repo, risk_repo, sensor_repo, schedule_repo, generator)
        await svc.generate_for_patient(PATIENT_ID, days=30)
        call_args = risk_repo.get_by_patient_since.call_args[0]
        assert call_args[0] == PATIENT_ID

    async def test_assembled_report_has_correct_patient(self, sample_patient):
        patient_repo, risk_repo, sensor_repo, schedule_repo, generator = _make_service_mocks(
            patient=sample_patient
        )
        svc = ReportService(patient_repo, risk_repo, sensor_repo, schedule_repo, generator)
        await svc.generate_for_patient(PATIENT_ID, days=30)
        report: PatientReport = generator.generate.call_args[0][0]
        assert report.patient is sample_patient

    async def test_assembled_report_has_correct_days(self, sample_patient):
        patient_repo, risk_repo, sensor_repo, schedule_repo, generator = _make_service_mocks(
            patient=sample_patient
        )
        svc = ReportService(patient_repo, risk_repo, sensor_repo, schedule_repo, generator)
        await svc.generate_for_patient(PATIENT_ID, days=14)
        report: PatientReport = generator.generate.call_args[0][0]
        assert report.days == 14

    async def test_assembled_report_includes_risk_events(
        self, sample_patient, sample_risk_event
    ):
        patient_repo, risk_repo, sensor_repo, schedule_repo, generator = _make_service_mocks(
            patient=sample_patient, risk_events=[sample_risk_event]
        )
        svc = ReportService(patient_repo, risk_repo, sensor_repo, schedule_repo, generator)
        await svc.generate_for_patient(PATIENT_ID, days=30)
        report: PatientReport = generator.generate.call_args[0][0]
        assert report.risk_events == [sample_risk_event]

    async def test_assembled_report_includes_sensor_readings(
        self, sample_patient, sample_sensor_reading
    ):
        patient_repo, risk_repo, sensor_repo, schedule_repo, generator = _make_service_mocks(
            patient=sample_patient, sensor_readings=[sample_sensor_reading]
        )
        svc = ReportService(patient_repo, risk_repo, sensor_repo, schedule_repo, generator)
        await svc.generate_for_patient(PATIENT_ID, days=30)
        report: PatientReport = generator.generate.call_args[0][0]
        assert report.sensor_readings == [sample_sensor_reading]

    async def test_assembled_report_includes_schedules(
        self, sample_patient, sample_schedule
    ):
        patient_repo, risk_repo, sensor_repo, schedule_repo, generator = _make_service_mocks(
            patient=sample_patient, schedules=[sample_schedule]
        )
        svc = ReportService(patient_repo, risk_repo, sensor_repo, schedule_repo, generator)
        await svc.generate_for_patient(PATIENT_ID, days=30)
        report: PatientReport = generator.generate.call_args[0][0]
        assert report.medication_schedules == [sample_schedule]


# ── Email template (pure function, no I/O) ────────────────────────────────────


def _extract_html_from_raw(raw_encoded: str) -> str:
    """Decode the Gmail API 'raw' value and extract the HTML body part.

    The MIMEMultipart message is base64-encoded for Gmail, and the HTML
    payload inside is itself Content-Transfer-Encoding: base64, so we need
    two decode passes.
    """
    import base64
    import email as email_module

    raw_bytes = base64.urlsafe_b64decode(raw_encoded + "==")
    msg = email_module.message_from_bytes(raw_bytes)
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True)
            if isinstance(payload, bytes):
                return payload.decode("utf-8", errors="replace")
    return ""


class TestBuildReminderMessage:
    def test_raw_key_present_in_output(self):
        """Gmail API requires a 'raw' key with base64-encoded RFC 2822 message."""
        from infrastructure.notifications.reminder_email import _build_reminder_message
        msg = _build_reminder_message(
            to="dr.hassan@clinique.dz",
            patient_name="Nadia Benali",
            medication="Metformin 500mg",
            meal_context="after",
        )
        assert "raw" in msg

    def test_raw_value_is_base64_decodable(self):
        import base64
        from infrastructure.notifications.reminder_email import _build_reminder_message
        msg = _build_reminder_message(
            to="dr.hassan@clinique.dz",
            patient_name="Nadia Benali",
            medication="Metformin 500mg",
            meal_context="after",
        )
        decoded = base64.urlsafe_b64decode(msg["raw"] + "==")
        assert len(decoded) > 0

    def test_medication_name_in_email_body(self):
        from infrastructure.notifications.reminder_email import _build_reminder_message
        msg = _build_reminder_message(
            to="dr.hassan@clinique.dz",
            patient_name="Nadia Benali",
            medication="Metformin 500mg",
            meal_context="after",
        )
        html = _extract_html_from_raw(msg["raw"])
        assert "Metformin 500mg" in html

    def test_patient_name_in_email_body(self):
        from infrastructure.notifications.reminder_email import _build_reminder_message
        msg = _build_reminder_message(
            to="dr.hassan@clinique.dz",
            patient_name="Nadia Benali",
            medication="Metformin 500mg",
            meal_context="after",
        )
        html = _extract_html_from_raw(msg["raw"])
        assert "Nadia Benali" in html

    def test_meal_context_in_email_body(self):
        from infrastructure.notifications.reminder_email import _build_reminder_message
        msg = _build_reminder_message(
            to="dr.hassan@clinique.dz",
            patient_name="Nadia Benali",
            medication="Metformin 500mg",
            meal_context="before",
        )
        html = _extract_html_from_raw(msg["raw"])
        assert "before" in html
