import asyncio
from typing import Optional
from google import genai
from google.genai import types
from src.tools import ToolHandler
from src import config
from src.config import AuthMode


class SophieLiveClient:
    """
    Client for interacting with the Gemini Multimodal Live API.
    Uses strictly google-genai SDK.
    Supports both AI Studio (API key) and Vertex AI authentication.
    """

    def __init__(
        self,
        auth_mode: Optional[AuthMode] = None,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
    ):
        """
        Initialize the client with authentication configuration.

        Args:
            auth_mode: Authentication mode (AI_STUDIO or VERTEX_AI).
                       Defaults to config.AUTH_MODE if not provided.
            api_key: Google API key for AI Studio mode.
            project_id: Google Cloud project ID for Vertex AI mode.
            location: Google Cloud location for Vertex AI mode.
        """
        # Use provided values or fall back to config
        self.auth_mode = auth_mode or config.AUTH_MODE
        self.api_key = api_key or config.GOOGLE_API_KEY
        self.project_id = project_id or config.PROJECT_ID
        self.location = location or config.LOCATION

        # Initialize client based on authentication mode
        if self.auth_mode == AuthMode.AI_STUDIO:
            if not self.api_key:
                raise ValueError("API key is required for AI Studio mode")
            self.client = genai.Client(api_key=self.api_key)
        else:  # VERTEX_AI
            self.client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location=self.location,
            )

        # Use appropriate model ID based on auth mode
        if self.auth_mode == AuthMode.AI_STUDIO:
            self.model_id = config.MODEL_ID_AI_STUDIO
        else:
            self.model_id = config.MODEL_ID_VERTEX_AI
        self.tool_handler = ToolHandler()
        
        # Map tool names to actual handler methods for execution
        self.tools_map = {
            "get_current_date_and_time": self.tool_handler.get_current_date_and_time,
            "google_search": self.tool_handler.google_search,
        }

    def _get_tools_definitions(self):
        """
        Returns the list of tool definitions for the model using types.Tool.

        For AI Studio mode, adds NON_BLOCKING behavior to enable async function
        execution (not supported on Vertex AI).
        """
        # Base function declarations
        base_declarations = [
            {
                "name": "get_current_date_and_time",
                "description": "Gets the current date and time.",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "google_search",
                "description": "Performs a Google search.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query."}
                    },
                    "required": ["query"]
                }
            },
        ]

        # Add NON_BLOCKING behavior for AI Studio mode only
        if self.auth_mode == AuthMode.AI_STUDIO:
            for decl in base_declarations:
                decl["behavior"] = "NON_BLOCKING"

        function_declarations = [
            types.FunctionDeclaration(**decl) for decl in base_declarations
        ]
        return [types.Tool(function_declarations=function_declarations)]

    async def connect(self):
        """Establishes a Live API session."""
        # Using direct fields instead of deprecated generation_config
        config_live = types.LiveConnectConfig(
            system_instruction=config.SYSTEM_INSTRUCTION,
            tools=self._get_tools_definitions(),
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=config.LIVE_CONFIG["voice_name"]
                    )
                ),
                language_code=config.LIVE_CONFIG["language_code"],
            ),
            # Interruption and barge-in
            explicit_vad_signal=config.LIVE_CONFIG["barge_in"],
            # Realtime behavior
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    silence_duration_ms=config.LIVE_CONFIG["silence_duration_ms"],
                    prefix_padding_ms=config.LIVE_CONFIG["prefix_padding_ms"],
                )
            ),
            # Proactivity
            proactivity=types.ProactivityConfig(
                proactive_audio=config.LIVE_CONFIG["proactive_audio"]
            ),
            # Transcriptions
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
        )
        
        return self.client.aio.live.connect(
            model=self.model_id,
            config=config_live
        )

    async def handle_tool_call(self, session, tool_call, scheduling: str = "INTERRUPT"):
        """
        Executes the tools and sends the responses back to the session.

        Args:
            session: The live session to send responses to.
            tool_call: The tool call object containing function calls.
            scheduling: Scheduling behavior for non-blocking functions (AI Studio only).
                       Options: "INTERRUPT", "WHEN_IDLE", "SILENT".
                       Default is "INTERRUPT" to immediately notify about the response.
        """
        function_responses = []
        for fc in tool_call.function_calls:
            name = fc.name
            args = fc.args
            call_id = fc.id  # SDK requires the call ID
            print(f"--- Sophie using tool: {name}({args}) ---")

            handler = self.tools_map.get(name)
            if handler:
                try:
                    # Tools are async
                    result = await handler(**args)

                    # For AI Studio mode with NON_BLOCKING functions,
                    # add scheduling to the response
                    if self.auth_mode == AuthMode.AI_STUDIO:
                        result["scheduling"] = scheduling

                    function_responses.append(
                        types.FunctionResponse(
                            name=name,
                            response=result,
                            id=call_id
                        )
                    )
                except Exception as e:
                    print(f"Error executing tool {name}: {e}")
            else:
                print(f"Tool {name} not found in map.")

        if function_responses:
            await session.send_tool_response(
                function_responses=function_responses
            )
