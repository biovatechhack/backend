"""
PatientProfileLoader
====================
Fetches the static patient metadata from the Supabase `patients` table and
returns a typed dict that is directly consumable by FeatureMapper.

Fields returned (match EBM training feature names):
    age, gender (0=M / 1=F), bmi, hba1c,
    has_hypertension, has_heart_disease, medication_count
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from infrastructure.supabase.client import get_supabase_client

logger = logging.getLogger(__name__)

# ── Safe defaults — used when patient not found (demo / test resilience) ──────
_DEFAULTS: Dict[str, Any] = {
    "age": 60,
    "gender": 0,           # 0 = Male
    "bmi": 27.0,
    "hba1c": 7.5,
    "has_hypertension": 0,
    "has_heart_disease": 0,
    "medication_count": 1,
}

# Keyword sets for comorbidity detection (lowercase, multi-language)
_HYPERTENSION_KW = {
    "hypertension", "hta", "hypertension artérielle", "high blood pressure",
    "ارتفاع الضغط", "ضغط الدم",
}
_HEART_KW = {
    "heart disease", "maladie cardiaque", "cardiopathie", "coronary",
    "قصور القلب", "مرض القلب", "cardiac",
}


class PatientProfileLoader:
    """
    Async loader for the 7 static patient features used by the EBM risk model.

    Usage::

        profile = await PatientProfileLoader.load(patient_id)
        # → {"age": 58, "gender": 1, "bmi": 26.1, "hba1c": 8.2, ...}
    """

    @staticmethod
    async def load(patient_id: str) -> Dict[str, Any]:
        """
        Fetch from Supabase and return a normalised feature dict.
        Falls back to _DEFAULTS on any error or if the patient is not found.
        """
        try:
            client = await get_supabase_client()
            result = (
                await client
                .table("patients")
                .select("*")
                .eq("id", patient_id)
                .limit(1)
                .execute()
            )
            if not result.data:
                logger.warning(
                    "[PatientProfileLoader] patient_id=%s not found — using defaults",
                    patient_id,
                )
                return _DEFAULTS.copy()

            return PatientProfileLoader._parse(result.data[0])

        except Exception as exc:  # pragma: no cover
            logger.error(
                "[PatientProfileLoader] Supabase fetch failed (%s) — using defaults", exc
            )
            return _DEFAULTS.copy()

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse(row: Dict[str, Any]) -> Dict[str, Any]:
        comorbidities: list = row.get("comorbidities") or []
        medications: list = row.get("medications") or []

        # Normalise comorbidities for keyword matching
        comorbidities_lower = {str(c).lower() for c in comorbidities}

        has_hypertension = int(
            any(kw in comorbidities_lower or any(kw in c for c in comorbidities_lower)
                for kw in _HYPERTENSION_KW)
        )
        has_heart_disease = int(
            any(kw in comorbidities_lower or any(kw in c for c in comorbidities_lower)
                for kw in _HEART_KW)
        )

        # gender: "M" / "F" in DB → 0 / 1 for the model
        raw_gender = str(row.get("gender", "M")).strip().upper()
        gender = 1 if raw_gender == "F" else 0

        return {
            "age":               int(row.get("age", 60)),
            "gender":            gender,
            "bmi":               float(row.get("bmi", 27.0)),
            "hba1c":             float(row.get("hba1c_last", 7.5)),
            "has_hypertension":  has_hypertension,
            "has_heart_disease": has_heart_disease,
            "medication_count":  len(medications),
        }
