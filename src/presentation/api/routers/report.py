from __future__ import annotations

import io
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from application.services.report_service import ReportService
from domain.exceptions import PatientNotFoundError
from infrastructure.pdf.reportlab_generator import ReportLabPdfGenerator
from infrastructure.supabase.medication_schedule_repository import (
    SupabaseMedicationScheduleRepository,
)
from infrastructure.supabase.patient_repository import SupabasePatientRepository
from infrastructure.supabase.risk_event_repository import SupabaseRiskEventRepository
from infrastructure.supabase.sensor_reading_repository import SupabaseSensorReadingRepository

report_router = APIRouter(prefix="/report", tags=["report"])


def _get_service() -> ReportService:
    return ReportService(
        patient_repo=SupabasePatientRepository(),
        risk_repo=SupabaseRiskEventRepository(),
        sensor_repo=SupabaseSensorReadingRepository(),
        schedule_repo=SupabaseMedicationScheduleRepository(),
        generator=ReportLabPdfGenerator(),
    )


ServiceDep = Annotated[ReportService, Depends(_get_service)]


@report_router.get("")
async def get_report(
    svc: ServiceDep,
    patient_id: str = Query(..., description="UUID of the patient"),
    days: int = Query(30, ge=1, le=365, description="Number of past days to include"),
) -> StreamingResponse:
    try:
        pdf_bytes = await svc.generate_for_patient(patient_id, days)
    except PatientNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found",
        ) from exc
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="rapport_nour.pdf"'},
    )
