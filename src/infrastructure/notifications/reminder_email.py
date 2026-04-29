from __future__ import annotations

import asyncio
import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from googleapiclient.errors import HttpError

from infrastructure.config.settings import settings
from infrastructure.notifications.gmail_adapter import _build_service
from infrastructure.supabase.patient_repository import SupabasePatientRepository

logger = logging.getLogger(__name__)

_TEMPLATE = """\
<html><body>
<h2>💊 ChronicCare Nour — Medication Reminder</h2>
<p>This is a reminder for patient <strong>{name}</strong> to take:</p>
<p style="font-size:18px;"><strong>{medication}</strong>
&nbsp;<span style="color:#555;">({meal_context} meal)</span></p>
<hr>
<p style="color:#888;font-size:12px;">
ChronicCare Nour automated reminder. Do not reply.
</p>
</body></html>
"""


def _build_reminder_message(
    to: str,
    patient_name: str,
    medication: str,
    meal_context: str,
) -> dict[str, str]:
    html = _TEMPLATE.format(name=patient_name, medication=medication, meal_context=meal_context)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"💊 Medication reminder: {medication}"
    msg["From"] = settings.GMAIL_SENDER
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))
    return {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()}


def _send_sync(to: str, patient_name: str, medication: str, meal_context: str) -> None:
    service = _build_service()
    body = _build_reminder_message(to, patient_name, medication, meal_context)
    service.users().messages().send(userId="me", body=body).execute()


async def send_push_reminder(patient_id: str, medication: str, meal_context: str) -> None:
    """Fetch patient, build a reminder email, send via Gmail.

    Errors are caught and logged — never raised — so a bad send never
    kills the scheduler thread.
    """
    try:
        patient = await SupabasePatientRepository().get_by_id(patient_id)
    except Exception as exc:
        logger.error("reminder: patient lookup failed patient_id=%s: %s", patient_id, exc)
        return

    if patient is None:
        logger.warning("reminder: patient not found patient_id=%s — skipping", patient_id)
        return

    try:
        await asyncio.to_thread(
            _send_sync,
            patient.doctor_email,
            patient.display_name,
            medication,
            meal_context,
        )
        logger.info(
            "reminder sent to=%s patient=%s medication=%s",
            patient.doctor_email,
            patient_id,
            medication,
        )
    except FileNotFoundError as exc:
        logger.warning("reminder: Gmail token missing — skipped: %s", exc)
    except HttpError as exc:
        logger.error("reminder: Gmail API error patient=%s: %s", patient_id, exc)
    except Exception as exc:
        logger.error("reminder: unexpected error patient=%s: %s", patient_id, exc)
