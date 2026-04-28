from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models.risk_models import RiskFeatures, RiskPrediction


class RiskClassifierPort(ABC):
    @abstractmethod
    def predict(self, features: RiskFeatures) -> RiskPrediction:
        """Classify patient risk level from clinical features."""
