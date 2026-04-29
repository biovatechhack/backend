from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.patient_report import PatientReport


class ReportGeneratorPort(ABC):
    @abstractmethod
    def generate(self, report: PatientReport) -> bytes:
        """Produce a PDF document from a PatientReport. Returns raw bytes."""
