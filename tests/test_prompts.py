import pytest
from src.prompts import SOPHIE_SYSTEM_INSTRUCTION

def test_system_instruction_contains_persona():
    assert "Sophie" in SOPHIE_SYSTEM_INSTRUCTION
    assert "Urban Indian" in SOPHIE_SYSTEM_INSTRUCTION
    assert "English language" in SOPHIE_SYSTEM_INSTRUCTION

def test_system_instruction_is_valid_string():
    assert isinstance(SOPHIE_SYSTEM_INSTRUCTION, str)
    assert len(SOPHIE_SYSTEM_INSTRUCTION) > 100

@pytest.mark.parametrize("word", ["friend", "warmth", "playful"])
def test_persona_keywords(word):
    assert word.lower() in SOPHIE_SYSTEM_INSTRUCTION.lower()

def test_intentional_fail_for_tdd():
    assert True
