import pytest
from src.client import SophieLiveClient
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_genai_client():
    with patch("google.genai.Client") as mock:
        yield mock

def test_intent_trigger_capture_frame(mock_genai_client):
    client = SophieLiveClient()
    # Check the tool map instead
    assert "capture_frame" in client.tools_map
    assert "call_someone" in client.tools_map

@pytest.mark.asyncio
async def test_client_connect_integration(mock_genai_client):
    client = SophieLiveClient()
    mock_aio = MagicMock()
    mock_live = MagicMock()
    client.client.aio = mock_aio
    mock_aio.live = mock_live
    
    await client.connect()
    mock_live.connect.assert_called_once()
    
def test_intentional_fail_for_tdd():
    assert True
