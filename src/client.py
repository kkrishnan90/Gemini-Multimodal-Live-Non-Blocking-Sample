import asyncio
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

    def __init__(self):
        # Validate configuration before initializing
        config.validate_config()

        # Initialize client based on authentication mode
        if config.AUTH_MODE == AuthMode.AI_STUDIO:
            self.client = genai.Client(api_key=config.GOOGLE_API_KEY)
        else:  # VERTEX_AI
            self.client = genai.Client(
                vertexai=True,
                project=config.PROJECT_ID,
                location=config.LOCATION
            )

        self.model_id = config.MODEL_ID
        self.tool_handler = ToolHandler()
        
        # Map tool names to actual handler methods for execution
        self.tools_map = {
            "get_current_date_and_time": self.tool_handler.get_current_date_and_time,
            "google_search": self.tool_handler.google_search,
        }

    def _get_tools_definitions(self):
        """Returns the list of tool definitions for the model using types.Tool."""
        function_declarations = [
            types.FunctionDeclaration(
                name="get_current_date_and_time",
                description="Gets the current date and time.",
                parameters={"type": "object", "properties": {}}
            ),
            types.FunctionDeclaration(
                name="google_search",
                description="Performs a Google search.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query."}
                    },
                    "required": ["query"]
                }
            ),
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

    async def handle_tool_call(self, session, tool_call):
        """Executes the tools and sends the responses back to the session."""
        function_responses = []
        for fc in tool_call.function_calls:
            name = fc.name
            args = fc.args
            call_id = fc.id # SDK requires the call ID
            print(f"--- Sophie using tool: {name}({args}) ---")
            
            handler = self.tools_map.get(name)
            if handler:
                try:
                    # Tools are async
                    result = await handler(**args)
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
