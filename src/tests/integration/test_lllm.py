import pytest
from infrastructure.intelligence.adapters.deepseek_adapter import DeepSeekAdapter

@pytest.mark.integration
async def test_llm_extraction():
    llm = DeepSeekAdapter()
    glossary = {
        "رأسي يدوخ": "dizziness",
        "عطشان بزاف": "excessive_thirst",
        "ما كليتش": "missed_meal"
    }
    result = await llm.extract_clinical_entities(
        "حاسس بدوخة وعطاش كثير من الصباح واسمي Ahmed Benaissa", 
        glossary
    )
    assert isinstance(result, dict)
    assert "symptoms" in result or "darija_confidence" in result
    print("✅ LLM extraction test passed")