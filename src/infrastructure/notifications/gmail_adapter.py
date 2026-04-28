from __future__ import annotations

import asyncio
import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import lru_cache
from pathlib import Path
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from abstraction.ports.notification_port import NotificationPort
from domain.entities.patient import Patient
from domain.models.risk_models import RiskPrediction
from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

_RISK_EMOJI = {"low": "🟢", "moderate": "🟡", "high": "🔴"}

_EMAIL_TEMPLATE = """\
<html><body>
<h2>{emoji} ChronicCare Nour — {level_upper} Risk Alert</h2>
<p>Patient <strong>{name}</strong> has been assessed as <strong>{level_upper} risk</strong>
with {confidence:.0%} confidence.</p>
<h3>Top contributing factors</h3>
<ul>
{features_html}
</ul>
<hr>
<p style="color:#888;font-size:12px;">
This alert was generated automatically by ChronicCare Nour.
Do not reply to this email.
</p>
</body></html>
"""


_PROJECT_ROOT = Path(__file__).parents[3]


@lru_cache(maxsize=1)
def _build_service() -> Any:
    raw_path = Path(settings.GMAIL_TOKEN_PATH)
    token_path = raw_path if raw_path.is_absolute() else _PROJECT_ROOT / raw_path
    if not token_path.exists():
        raise FileNotFoundError(
            f"Gmail token not found: {token_path}\n"
            "Run: hackathon-env/bin/python scripts/setup_gmail_oauth.py"
        )

    import json
    raw = json.loads(token_path.read_text())
    creds = Credentials.from_authorized_user_info(raw, settings.GMAIL_SCOPES)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _build_message(to: str, patient_name: str, prediction: RiskPrediction) -> dict[str, str]:
    level = prediction.risk_level
    emoji = _RISK_EMOJI.get(level, "⚠️")
    features_html = "\n".join(f"<li>{f}</li>" for f in prediction.top_features)

    html = _EMAIL_TEMPLATE.format(
        emoji=emoji,
        level_upper=level.upper(),
        name=patient_name,
        confidence=prediction.confidence,
        features_html=features_html or "<li>N/A</li>",
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{emoji} ChronicCare Nour — {level.upper()} Risk Alert: {patient_name}"
    msg["From"] = settings.GMAIL_SENDER
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))

    raw_bytes = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw_bytes}


def _send_sync(to: str, patient_name: str, prediction: RiskPrediction) -> None:
    service = _build_service()
    body = _build_message(to, patient_name, prediction)
    service.users().messages().send(userId="me", body=body).execute()


class GmailNotificationAdapter(NotificationPort):
    """Sends HTML alert emails via the Gmail API using an OAuth2 token."""

    @property
    def channel_name(self) -> str:
        return "email"

    async def send(self, *, patient: Patient, prediction: RiskPrediction) -> bool:
        if prediction.risk_level != "high":
            return False

        recipient = patient.doctor_email
        try:
            await asyncio.to_thread(_send_sync, recipient, patient.display_name, prediction)
            logger.info("gmail alert sent to %s for patient %s", recipient, patient.id)
            return True
        except FileNotFoundError as exc:
            logger.warning("Gmail token missing — email alert skipped: %s", exc)
            return False
        except HttpError as exc:
            logger.error("Gmail API error sending to %s: %s", recipient, exc)
            return False
        except Exception as exc:
            logger.error("Unexpected error sending gmail alert: %s", exc)
            return False
