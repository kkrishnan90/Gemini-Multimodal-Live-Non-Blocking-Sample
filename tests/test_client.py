import pytest
from src.client import SophieLiveClient
from src.config import AuthMode
from google.genai import types
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.fixture
def client_ai_studio():
    """Create an AI Studio client for testing."""
    with patch("google.genai.Client"):
        return SophieLiveClient(
            auth_mode=AuthMode.AI_STUDIO,
            api_key="test-api-key"
        )


@pytest.fixture
def client_vertex_ai():
    """Create a Vertex AI client for testing."""
    with patch("google.genai.Client"):
        return SophieLiveClient(
            auth_mode=AuthMode.VERTEX_AI,
            project_id="test-project",
            location="us-central1"
        )


def test_ai_studio_client_initialization(client_ai_studio):
    """Test AI Studio client uses correct model ID with models/ prefix."""
    # AI Studio requires "models/" prefix for the model name
    assert client_ai_studio.model_id == "models/gemini-2.5-flash-native-audio-preview-12-2025"
    assert client_ai_studio.auth_mode == AuthMode.AI_STUDIO
    assert len(client_ai_studio.tools_map) == 1  # get_current_date_and_time


def test_vertex_ai_client_initialization(client_vertex_ai):
    """Test Vertex AI client uses correct model ID."""
    assert client_vertex_ai.model_id == "gemini-live-2.5-flash-preview-native-audio-09-2025"
    assert client_vertex_ai.auth_mode == AuthMode.VERTEX_AI
    assert len(client_vertex_ai.tools_map) == 1  # get_current_date_and_time


def test_tools_definitions_ai_studio(client_ai_studio):
    """Test AI Studio tools have NON_BLOCKING behavior."""
    tools = client_ai_studio._get_tools_definitions()
    assert len(tools) == 1

    # Check function declarations have NON_BLOCKING for AI Studio
    func_tool = tools[0]
    assert len(func_tool.function_declarations) == 1
    assert func_tool.function_declarations[0].name == "get_current_date_and_time"
    assert func_tool.function_declarations[0].behavior.value == "NON_BLOCKING"


def test_tools_definitions_vertex_ai(client_vertex_ai):
    """Test Vertex AI tools don't have NON_BLOCKING behavior."""
    tools = client_vertex_ai._get_tools_definitions()
    assert len(tools) == 1

    # Check function declarations don't have NON_BLOCKING for Vertex AI
    func_tool = tools[0]
    assert len(func_tool.function_declarations) == 1
    assert func_tool.function_declarations[0].name == "get_current_date_and_time"
    # Vertex AI shouldn't have behavior set (or it's None)
    assert func_tool.function_declarations[0].behavior is None


@pytest.mark.asyncio
async def test_handle_tool_call_ai_studio(client_ai_studio):
    """Test tool call handling for AI Studio adds scheduling as top-level param."""
    mock_session = MagicMock()
    mock_session.send_tool_response = AsyncMock()

    mock_fc = MagicMock()
    mock_fc.name = "get_current_date_and_time"
    mock_fc.args = {}
    mock_fc.id = "test-id-1"

    mock_tool_call = MagicMock()
    mock_tool_call.function_calls = [mock_fc]

    await client_ai_studio.handle_tool_call(mock_session, mock_tool_call)

    assert mock_session.send_tool_response.called
    args, kwargs = mock_session.send_tool_response.call_args

    # Should have 1 response for the valid tool
    assert len(kwargs['function_responses']) == 1

    # AI Studio should have scheduling as a top-level FunctionResponse param
    response = kwargs['function_responses'][0]
    assert response.name == "get_current_date_and_time"
    # scheduling should be a top-level property, not inside response dict
    assert response.scheduling == types.FunctionResponseScheduling.INTERRUPT
    # response dict should NOT contain scheduling
    assert "scheduling" not in response.response


@pytest.mark.asyncio
async def test_handle_tool_call_vertex_ai(client_vertex_ai):
    """Test tool call handling for Vertex AI doesn't add scheduling."""
    mock_session = MagicMock()
    mock_session.send_tool_response = AsyncMock()

    mock_fc = MagicMock()
    mock_fc.name = "get_current_date_and_time"
    mock_fc.args = {}
    mock_fc.id = "test-id-1"

    mock_tool_call = MagicMock()
    mock_tool_call.function_calls = [mock_fc]

    await client_vertex_ai.handle_tool_call(mock_session, mock_tool_call)

    assert mock_session.send_tool_response.called
    args, kwargs = mock_session.send_tool_response.call_args

    # Should have 1 response
    assert len(kwargs['function_responses']) == 1

    # Vertex AI should NOT have scheduling
    response = kwargs['function_responses'][0]
    assert response.name == "get_current_date_and_time"
    # scheduling should be None for Vertex AI
    assert response.scheduling is None
    # response dict should NOT contain scheduling
    assert "scheduling" not in response.response


@pytest.mark.asyncio
async def test_handle_unknown_tool(client_ai_studio):
    """Test that unknown tools are skipped."""
    mock_session = MagicMock()
    mock_session.send_tool_response = AsyncMock()

    mock_fc = MagicMock()
    mock_fc.name = "unknown_tool"
    mock_fc.args = {}
    mock_fc.id = "test-id-1"

    mock_tool_call = MagicMock()
    mock_tool_call.function_calls = [mock_fc]

    await client_ai_studio.handle_tool_call(mock_session, mock_tool_call)

    # Should not call send_tool_response since no valid tools
    assert not mock_session.send_tool_response.called
