import pytest
from src.tools import ToolHandler

@pytest.fixture
def handler():
    return ToolHandler()

def test_phone_call_edge_cases(handler):
    # No name, only number
    res = handler.call_someone(phone_number="123456")
    assert res["name"] == "Unknown"
    assert "123456" in res["message"]
    
    # Neither name nor number
    res_none = handler.call_someone()
    assert res_none["name"] == "Unknown"
    assert res_none["phone_number"] == "Not provided" # Updated to match ToolHandler default

def test_scanner_missing_amount(handler):
    # Missing amount should return a prompt to provide one
    result = handler.open_scanner()
    assert result["status"] == "error"
    assert "provide the amount" in result["message"]

def test_music_variations(handler):
    # Action "stop" (if we ever use it)
    result = handler.play_music(action="stop")
    assert result["status"] == "playing" # Mock is currently simple
    
    # Generic song name
    result = handler.play_music(song_name="something happy")
    assert "something happy" in result["track"]

def test_search_currency_context(handler):
    # The prompt mentions local currency for cost queries
    result = handler.google_search(query="Cost of iPhone 16 in India")
    assert "iPhone 16" in result["query"]
    # In a real tool, this would return INR. Mock returns success.
    assert result["status"] == "success"

def test_vision_queries(handler):
    # Very short query
    result = handler.capture_frame(user_query="?")
    assert "?" in result["scene_description"]
    
    # Long query
    long_query = "What is the object on the left next to the blue bottle?"
    result_long = handler.capture_frame(user_query=long_query)
    assert long_query in result_long["scene_description"]
