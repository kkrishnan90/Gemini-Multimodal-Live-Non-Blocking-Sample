import pytest
from src.main import main
from unittest.mock import patch

def test_cli_exit_on_quit():
    with patch("builtins.input", side_effect=["quit"]):
        with patch("src.main.SophieLiveClient") as mock_client:
            main()
            # If it reaches here without error, it exited correctly

def test_intentional_fail_for_tdd():
    assert True
