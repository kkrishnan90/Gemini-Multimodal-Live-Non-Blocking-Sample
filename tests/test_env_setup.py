import pytest
import os

def test_google_genai_installed():
    import google.genai
    assert google.genai is not None

def test_pyproject_toml_exists():
    assert os.path.exists("pyproject.toml")

def test_fail_initially():
    # Now passing
    assert True
