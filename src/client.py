import asyncio
from google import genai
from google.genai import types
from src.tools import ToolHandler
from src import config

class SophieLiveClient:
    """
    Client for interacting with the Gemini Multimodal Live API.
    Uses strictly google-genai SDK.
    """

    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            project=config.PROJECT_ID,
            location=config.LOCATION
        )
        self.model_id = config.MODEL_ID
        self.tool_handler = ToolHandler()
        
        # Map tool names to actual handler methods for execution
        self.tools_map = {
            "close_camera": self.tool_handler.close_camera,
            "take_photo": self.tool_handler.take_photo,
            "start_video": self.tool_handler.start_video,
            "stop_video": self.tool_handler.stop_video,
            "stop_b": self.tool_handler.stop_b,
            "start_observe_mode": self.tool_handler.start_observe_mode,
            "stop_observe_mode": self.tool_handler.stop_observe_mode,
            "start_translation_mode": self.tool_handler.start_translation_mode,
            "start_meeting_mode": self.tool_handler.start_meeting_mode,
            "get_current_date_and_time": self.tool_handler.get_current_date_and_time,
            "play_music": self.tool_handler.play_music,
            "capture_frame": self.tool_handler.capture_frame,
            "log_my_meal": self.tool_handler.log_my_meal,
            "call_someone": self.tool_handler.call_someone,
            "confirm_call": self.tool_handler.confirm_call,
            "send_message": self.tool_handler.send_message,
            "open_scanner": self.tool_handler.open_scanner,
            "google_search": self.tool_handler.google_search,
            "search_nearby_places": self.tool_handler.search_nearby_places
        }

    def _get_tools_definitions(self):
        """Returns the list of tool definitions for the model using types.Tool."""
        function_declarations = [
            types.FunctionDeclaration(
                name="close_camera",
                description="Closes the camera.",
                parameters={"type": "object", "properties": {}}
            ),
            types.FunctionDeclaration(
                name="take_photo",
                description="Takes a photo.",
                parameters={"type": "object", "properties": {}}
            ),
            types.FunctionDeclaration(
                name="start_video",
                description="Starts recording video.",
                parameters={"type": "object", "properties": {}}
            ),
            types.FunctionDeclaration(
                name="stop_video",
                description="Stops recording video.",
                parameters={"type": "object", "properties": {}}
            ),
            types.FunctionDeclaration(
                name="stop_b",
                description="Ends the session.",
                parameters={"type": "object", "properties": {}}
            ),
            types.FunctionDeclaration(
                name="start_observe_mode",
                description="Starts observe mode.",
                parameters={"type": "object", "properties": {}}
            ),
            types.FunctionDeclaration(
                name="stop_observe_mode",
                description="Stops observe mode.",
                parameters={"type": "object", "properties": {}}
            ),
            types.FunctionDeclaration(
                name="start_translation_mode",
                description="Starts translation mode.",
                parameters={"type": "object", "properties": {}}
            ),
            types.FunctionDeclaration(
                name="start_meeting_mode",
                description="Starts meeting mode.",
                parameters={"type": "object", "properties": {}}
            ),
            types.FunctionDeclaration(
                name="get_current_date_and_time",
                description="Gets the current date and time.",
                parameters={"type": "object", "properties": {}}
            ),
            types.FunctionDeclaration(
                name="play_music",
                description="Plays music.",
                parameters={
                    "type": "object",
                    "properties": {
                        "song_name": {"type": "string", "description": "The name of the song to play."}
                    }
                }
            ),
            types.FunctionDeclaration(
                name="capture_frame",
                description="Captures a frame for vision analysis.",
                parameters={
                    "type": "object",
                    "properties": {
                        "user_query": {"type": "string", "description": "The user's query about the scene."}
                    },
                    "required": ["user_query"]
                }
            ),
            types.FunctionDeclaration(
                name="log_my_meal",
                description="Logs a meal.",
                parameters={"type": "object", "properties": {}}
            ),
            types.FunctionDeclaration(
                name="call_someone",
                description="Initiates a phone call.",
                parameters={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "The name of the person to call."},
                        "phone_number": {"type": "string", "description": "The phone number to call."}
                    }
                }
            ),
            types.FunctionDeclaration(
                name="confirm_call",
                description="Confirms and places a phone call.",
                parameters={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "The confirmed name."},
                        "phone_number": {"type": "string", "description": "The confirmed phone number."}
                    },
                    "required": ["name", "phone_number"]
                }
            ),
            types.FunctionDeclaration(
                name="send_message",
                description="Sends a message to a remote agent.",
                parameters={
                    "type": "object",
                    "properties": {
                        "agent_name": {"type": "string", "description": "The name of the agent."},
                        "query": {"type": "string", "description": "The message/query."}
                    },
                    "required": ["agent_name", "query"]
                }
            ),
            types.FunctionDeclaration(
                name="open_scanner",
                description="Opens the scanner for payment.",
                parameters={
                    "type": "object",
                    "properties": {
                        "amount": {"type": "string", "description": "The amount to scan."}
                    },
                    "required": ["amount"]
                }
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
            types.FunctionDeclaration(
                name="search_nearby_places",
                description="Searches for nearby places.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The place to search for."}
                    },
                    "required": ["query"]
                }
            )
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
                    # Mock tools are synchronous in our implementation
                    result = handler(**args)
                    function_responses.append(
                        types.FunctionResponse(
                            name=name,
                            response=result,
                            id=call_id # Include the ID
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

    async def update_persona(self, session, instruction):
        """Updates the system instruction dynamically."""
        print(f"--- Sending Client Content (Update Persona): {instruction[:50]}... ---")
        await session.send_client_content(
            turns=[types.Content(
                role="system",
                parts=[types.Part(text=instruction)]
            )],
            turn_complete=True
        )
        print("--- Persona Update Sent Successfully ---")