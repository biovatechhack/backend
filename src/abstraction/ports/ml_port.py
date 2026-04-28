from abc import ABC, abstractmethod
from typing import Dict, Any

class RiskScorer(ABC):
    """Port for any risk scorer (Mock or Real EBM)"""

    @abstractmethod
    async def score(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Return {'risk': 'LOW'|'MODERATE'|'HIGH', 'confidence': float, 'top_features': list}"""
        pass
    