import pytest
from src.auth import check_adc
import os

def test_check_adc_success(monkeypatch):
    # Ensure the environment variable is set for the test (or rely on system if it's there)
    # The prompt says it IS configured.
    assert check_adc() is True

def test_check_adc_failure(monkeypatch):
    from unittest.mock import patch
    with patch("google.auth.default", side_effect=Exception("Auth error")):
         assert check_adc() is False

def test_check_adc_no_credentials(monkeypatch):
    from unittest.mock import patch
    with patch("google.auth.default", return_value=(None, None)):
         assert check_adc() is False
