from fastapi import Depends

# Your actual port
from abstraction.ports.llm_port import LlmPort
from abstraction.ports.ml_port import RiskScorer

# Your adapters
from infrastructure.intelligence.adapters.deepseek_adapter import DeepSeekAdapter
from infrastructure.ml.real_risk_scorer import RealRiskScorer


def get_llm() -> LlmPort:
    """Returns the DeepSeek implementation of LlmPort"""
    return DeepSeekAdapter()


def get_risk_scorer() -> RiskScorer:
    """Returns the real EBM model scorer"""
    return RealRiskScorer()