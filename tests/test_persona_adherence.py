import pytest
from src.prompts import SOPHIE_SYSTEM_INSTRUCTION

def test_persona_prohibits_ai_claims():
    assert "Never claim to be created by Gemini, Google" in SOPHIE_SYSTEM_INSTRUCTION
    assert "Identify as \"Sophie\"" in SOPHIE_SYSTEM_INSTRUCTION

def test_persona_strict_english():
    assert "MUST STRICTLY respond back ONLY in English" in SOPHIE_SYSTEM_INSTRUCTION

def test_intentional_fail_for_tdd():
    assert True
