from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models.risk_models import RiskFeatures, RiskPrediction


class RiskClassifierPort(ABC):
    @abstractmethod
    def predict(self, features: RiskFeatures) -> RiskPrediction:
        """Classify patient risk level from clinical features."""
