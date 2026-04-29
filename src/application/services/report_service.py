from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from abstraction.ports.report_generator_port import ReportGeneratorPort
from abstraction.repositories.medication_schedule_repository_port import (
    MedicationScheduleRepositoryPort,
)
from abstraction.repositories.patient_repository_port import PatientRepositoryPort
from abstraction.repositories.risk_event_repository_port import RiskEventRepositoryPort
from abstraction.repositories.sensor_reading_repository_port import SensorReadingRepositoryPort
from domain.entities.patient_report import PatientReport
from domain.exceptions import PatientNotFoundError

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(
        self,
        patient_repo: PatientRepositoryPort,
        risk_repo: RiskEventRepositoryPort,
        sensor_repo: SensorReadingRepositoryPort,
        schedule_repo: MedicationScheduleRepositoryPort,
        generator: ReportGeneratorPort,
    ) -> None:
        self._patient_repo = patient_repo
        self._risk_repo = risk_repo
        self._sensor_repo = sensor_repo
        self._schedule_repo = schedule_repo
        self._generator = generator

    async def generate_for_patient(self, patient_id: str, days: int) -> bytes:
        since = datetime.now(UTC) - timedelta(days=days)

        patient = await self._patient_repo.get_by_id(patient_id)
        if patient is None:
            raise PatientNotFoundError(patient_id)

        risk_events, sensor_readings, schedules = await asyncio.gather(
            self._risk_repo.get_by_patient_since(patient_id, since),
            self._sensor_repo.get_by_patient_since(patient_id, since),
            self._schedule_repo.get_active_by_patient(patient_id),
        )

        report = PatientReport(
            patient=patient,
            risk_events=risk_events,
            sensor_readings=sensor_readings,
            medication_schedules=schedules,
            days=days,
            generated_at=datetime.now(UTC),
        )
        pdf_bytes = self._generator.generate(report)
        logger.info(
            "report.generated patient=%s days=%d events=%d readings=%d bytes=%d",
            patient_id, days, len(risk_events), len(sensor_readings), len(pdf_bytes),
        )
        return pdf_bytes
