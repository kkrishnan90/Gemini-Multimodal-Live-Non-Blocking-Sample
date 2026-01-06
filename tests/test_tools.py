import pytest
from src.tools import ToolHandler

@pytest.fixture
def handler():
    return ToolHandler()

def test_camera_and_video(handler):
    assert handler.close_camera()["status"] == "success"
    assert handler.take_photo()["status"] == "success"
    assert handler.start_video()["status"] == "success"
    assert handler.stop_video()["status"] == "success"

def test_app_control_modes(handler):
    assert handler.stop_b()["status"] == "session_ended"
    assert handler.start_observe_mode()["status"] == "active"
    assert handler.stop_observe_mode()["status"] == "inactive"
    assert handler.start_translation_mode()["status"] == "active"
    assert handler.start_meeting_mode()["status"] == "active"

def test_date_and_time(handler):
    result = handler.get_current_date_and_time()
    assert "date" in result
    assert "time" in result
    assert result["timezone"] == "IST"

def test_music(handler):
    result = handler.play_music(song_name="Vibe")
    assert result["status"] == "playing"
    assert result["track"] == "Vibe"
    
    result_default = handler.play_music()
    assert "playlist" in result_default["track"]

def test_vision(handler):
    result = handler.capture_frame(user_query="flower")
    assert "flower" in result["scene_description"]

def test_meal_logging(handler):
    assert handler.log_my_meal()["status"] == "camera_open"

def test_phone_calls(handler):
    # Initial call request
    res = handler.call_someone(name="John")
    assert res["status"] == "confirming"
    assert res["name"] == "John"
    
    # Confirmation
    res_conf = handler.confirm_call(name="John", phone_number="12345")
    assert res_conf["status"] == "dialing"
    assert res_conf["phone_number"] == "12345"

def test_messaging(handler):
    result = handler.send_message(agent_name="WeatherAgent", query="temp")
    assert result["status"] == "sent"
    assert result["agent"] == "WeatherAgent"

def test_scanner(handler):
    result = handler.open_scanner(amount="500 INR")
    assert result["status"] == "scanner_open"
    assert result["amount"] == "500 INR"

def test_search_tools(handler):
    result_g = handler.google_search(query="latest AI news")
    assert result_g["status"] == "success"
    assert "latest AI news" in result_g["result"]
    
    result_n = handler.search_nearby_places(query="cafe")
    assert result_n["status"] == "success"
    assert len(result_n["results"]) > 0