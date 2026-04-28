from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.patient import Patient
from domain.models.risk_models import RiskPrediction


class NotificationPort(ABC):
    """Single-channel outbound notification adapter (FCM, email, SMS, …)."""

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Stable identifier returned in alerts_sent, e.g. 'fcm', 'email', 'sms'."""

    @abstractmethod
    async def send(self, *, patient: Patient, prediction: RiskPrediction) -> bool:
        """Deliver the alert. Returns True on success. Never raises — log and return False."""
