import pytest
import asyncio
from src.client import SophieLiveClient
from google.genai import types
from unittest.mock import MagicMock, patch, AsyncMock

@pytest.fixture
def client():
    with patch("google.genai.Client"):
        return SophieLiveClient()

def test_client_initialization(client):
    assert client.model_id == "gemini-live-2.5-flash-native-audio"
    assert len(client.tools_map) == 19

def test_tools_definitions(client):
    tools = client._get_tools_definitions()
    assert len(tools) == 1
    assert len(tools[0].function_declarations) == 19
    assert any(d.name == "capture_frame" for d in tools[0].function_declarations)

@pytest.mark.asyncio

async def test_handle_multiple_tool_calls(client):

    mock_session = MagicMock()

    mock_session.send_tool_response = AsyncMock()

    

    mock_fc1 = MagicMock()

    mock_fc1.name = "get_current_date_and_time"

    mock_fc1.args = {}

    mock_fc1.id = "1"

    

    mock_fc2 = MagicMock()

    mock_fc2.name = "play_music"

    mock_fc2.args = {"song_name": "Test"}

    mock_fc2.id = "2"

    

    mock_tool_call = MagicMock()

    mock_tool_call.function_calls = [mock_fc1, mock_fc2]

    

    await client.handle_tool_call(mock_session, mock_tool_call)

    assert mock_session.send_tool_response.called

    args, kwargs = mock_session.send_tool_response.call_args

    assert len(kwargs['function_responses']) == 2


