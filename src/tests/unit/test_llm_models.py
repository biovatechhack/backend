from __future__ import annotations

import pytest

from src.domain.models.llm_models import EntityExtractionResult


def test_defaults_are_empty_collections() -> None:
    result = EntityExtractionResult()
    assert result.medications == []
    assert result.symptoms == []
    assert result.vital_signs == {}
    assert result.risk_flags == []


def test_populated_fields() -> None:
    result = EntityExtractionResult(
        medications=["metformin 500mg", "lisinopril"],
        symptoms=["fatigue", "polyuria"],
        vital_signs={"blood_pressure": "140/90", "glucose": "8.2 mmol/L"},
        risk_flags=["HbA1c_elevated"],
    )
    assert "metformin 500mg" in result.medications
    assert "fatigue" in result.symptoms
    assert result.vital_signs["glucose"] == "8.2 mmol/L"
    assert "HbA1c_elevated" in result.risk_flags


def test_model_validate_from_dict() -> None:
    data = {
        "medications": ["aspirin"],
        "symptoms": [],
        "vital_signs": {"hr": "72 bpm"},
        "risk_flags": [],
    }
    result = EntityExtractionResult.model_validate(data)
    assert result.medications == ["aspirin"]
    assert result.vital_signs == {"hr": "72 bpm"}


def test_model_validate_partial_dict_uses_defaults() -> None:
    result = EntityExtractionResult.model_validate({"medications": ["warfarin"]})
    assert result.medications == ["warfarin"]
    assert result.symptoms == []
    assert result.risk_flags == []


def test_instances_do_not_share_mutable_defaults() -> None:
    a = EntityExtractionResult()
    b = EntityExtractionResult()
    a.medications.append("metformin")
    assert b.medications == []


def test_model_dump_round_trip() -> None:
    original = EntityExtractionResult(medications=["insulin"], risk_flags=["hypoglycemia_risk"])
    restored = EntityExtractionResult.model_validate(original.model_dump())
    assert restored == original
