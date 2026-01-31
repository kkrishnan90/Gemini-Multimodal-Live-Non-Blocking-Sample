import asyncio
import json
import logging
import os
import subprocess
from typing import Optional
from google import genai
from google.genai import types
from google.oauth2 import credentials as oauth2_credentials
from src.tools import ToolHandler
from src import config
from src.config import AuthMode

logger = logging.getLogger("sophie-client")


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
            # AI Studio requires api_version="v1beta" for Live API
            self.client = genai.Client(
                api_key=self.api_key,
                http_options={"api_version": "v1beta"},
            )
        else:  # VERTEX_AI
            # Get access token from gcloud
            credentials = self._get_gcloud_credentials()

            self.client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location=self.location,
                credentials=credentials,
                http_options={"base_url": f"https://{config.VERTEX_API_ENDPOINT}"},
            )
            logger.info(f"Using Vertex AI endpoint: {config.VERTEX_API_ENDPOINT}")

        # Use appropriate model ID based on auth mode
        # AI Studio requires "models/" prefix for the model name
        if self.auth_mode == AuthMode.AI_STUDIO:
            model_name = config.MODEL_ID_AI_STUDIO
            # Add models/ prefix if not present (required for AI Studio)
            if not model_name.startswith("models/"):
                model_name = f"models/{model_name}"
            self.model_id = model_name
        else:
            self.model_id = config.MODEL_ID_VERTEX_AI
        self.tool_handler = ToolHandler()
        
        # Map tool names to actual handler methods for execution
        # Note: google_search is NOT here - it's a built-in server-side tool
        self.tools_map = {
            "get_current_date_and_time": self.tool_handler.get_current_date_and_time,
            "get_lucky_number": self.tool_handler.get_lucky_number,
            "action_trigger": self.tool_handler.action_trigger,
        }

    def _get_gcloud_credentials(self):
        """Get credentials using gcloud auth print-access-token."""
        try:
            result = subprocess.run(
                ["gcloud", "auth", "print-access-token"],
                capture_output=True,
                text=True,
                check=True
            )
            access_token = result.stdout.strip()
            logger.info("Using bearer token from gcloud auth print-access-token")
            return oauth2_credentials.Credentials(token=access_token)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get access token from gcloud: {e}")
            raise ValueError("Failed to get access token. Run: gcloud auth login")

    def _get_tools_definitions(self):
        """
        Returns the list of tool definitions for the model using types.Tool.

        Includes:
        - Custom function declarations (with handlers in tools_map)
        - Built-in GoogleSearch tool (server-side, no handler needed)
        """
        # Function declarations for custom tools
        function_declarations = [
            {
                "name": "get_current_date_and_time",
                "description": "Gets the current date and time.",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "get_lucky_number",
                "description": "Generates a personalized lucky number, color, and zodiac influence.",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "action_trigger",
                "description": "Routes the identified delivery partner issue to the appropriate handler. Call this after confirming the issue type with the delivery partner.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "issue_type": {
                            "type": "string",
                            "description": "The identified issue type (e.g., RESTAURANT_IS_DELAYING_ORDER, VEHICLE_BREAKDOWN, ITEM_OUT_OF_STOCK, etc.)"
                        }
                    },
                    "required": ["issue_type"]
                }
            },
        ]

        # Add NON_BLOCKING behavior for AI Studio mode only
        if self.auth_mode == AuthMode.AI_STUDIO:
            for decl in function_declarations:
                decl["behavior"] = types.Behavior.NON_BLOCKING

        declarations = [
            types.FunctionDeclaration(**decl) for decl in function_declarations
        ]

        # Log tool declarations for debugging
        logger.info(f"Registering {len(declarations)} tools: {[d.name for d in declarations]}")

        return [types.Tool(function_declarations=declarations)]

    async def connect(self):
        """Establishes a Live API session."""
        # AI Studio has limited language code support - use en-US
        # Vertex AI supports en-IN and other language codes
        language_code = config.LIVE_CONFIG["language_code"]
        if self.auth_mode == AuthMode.AI_STUDIO and language_code not in ["en-US", "en"]:
            language_code = "en-US"

        # Build common config parameters
        config_params = {
            "system_instruction": config.SYSTEM_INSTRUCTION,
            "tools": self._get_tools_definitions(),
            "response_modalities": ["AUDIO"],
            "speech_config": types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=config.LIVE_CONFIG["voice_name"]
                    )
                ),
                language_code=language_code,
            ),
            # VAD (Voice Activity Detection) configuration
            "realtime_input_config": types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=config.LIVE_CONFIG["vad_disabled"],
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH
                    if config.LIVE_CONFIG["start_of_speech_sensitivity"].upper() == "HIGH"
                    else types.StartSensitivity.START_SENSITIVITY_LOW,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH
                    if config.LIVE_CONFIG["end_of_speech_sensitivity"].upper() == "HIGH"
                    else types.EndSensitivity.END_SENSITIVITY_LOW,
                    silence_duration_ms=config.LIVE_CONFIG["silence_duration_ms"],
                    prefix_padding_ms=config.LIVE_CONFIG["prefix_padding_ms"],
                ),
                # Enable barge-in (interruption) - user speech interrupts model response
                activity_handling=types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS
                if config.LIVE_CONFIG["barge_in"]
                else types.ActivityHandling.NO_INTERRUPTION,
            ),
            # Transcriptions
            "input_audio_transcription": types.AudioTranscriptionConfig(),
            "output_audio_transcription": types.AudioTranscriptionConfig(),
        }

        # Vertex AI specific parameters (not supported in Gemini API / AI Studio)
        if self.auth_mode == AuthMode.VERTEX_AI:
            # Proactivity is Vertex AI specific
            config_params["proactivity"] = types.ProactivityConfig(
                proactive_audio=config.LIVE_CONFIG["proactive_audio"]
            )

        config_live = types.LiveConnectConfig(**config_params)

        # Log session init payload as raw JSON
        logger.info("=" * 60)
        logger.info("SESSION INIT PAYLOAD (JSON)")
        logger.info("=" * 60)
        logger.info(f"Model: {self.model_id}")
        logger.info(f"Auth Mode: {self.auth_mode.value}")

        # Convert config to JSON-serializable dict and log
        try:
            config_dict = config_live.model_dump(exclude_none=True)
            # Remove system_instruction from log (too verbose)
            if "system_instruction" in config_dict:
                config_dict["system_instruction"] = "[TRUNCATED]"
            # Format tools for readability
            if "tools" in config_dict:
                tool_names = []
                for tool in config_dict.get("tools", []):
                    if "function_declarations" in tool:
                        for fd in tool["function_declarations"]:
                            tool_names.append(fd.get("name", "unknown"))
                config_dict["tools"] = f"[{len(tool_names)} tools: {', '.join(tool_names)}]"
            logger.info(f"Config JSON:\n{json.dumps(config_dict, indent=2, default=str)}")
        except Exception as e:
            logger.warning(f"Failed to serialize config to JSON: {e}")
        logger.info("=" * 60)

        return self.client.aio.live.connect(
            model=self.model_id,
            config=config_live
        )

    async def handle_tool_call(self, session, tool_call):
        """
        Handles tool calls and sends responses back to the session.

        Args:
            session: The live session to send responses to.
            tool_call: The tool call object containing function calls.
        """
        for fc in tool_call.function_calls:
            name = fc.name
            args = fc.args
            call_id = fc.id

            handler = self.tools_map.get(name)
            if not handler:
                logger.warning(f"Tool {name} not found in map.")
                continue

            # Send interim response to let model acknowledge the request
            from datetime import datetime
            interim_ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            interim_response = types.FunctionResponse(
                name=name,
                response={
                    "status": "PROCESSING",
                    "message": "I'm working on it. Please wait a moment."
                },
                id=call_id
            )
            await session.send_tool_response(function_responses=[interim_response])
            logger.info(f"[{interim_ts}] [TOOL_INTERIM] Sent interim response for {name}")

            # Execute tool (runs in background via asyncio.create_task in server.py)
            try:
                from datetime import datetime
                start_ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                logger.info(f"[{start_ts}] [TOOL_START] {name} - executing...")

                result = await handler(**args)

                end_ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                logger.info(f"[{end_ts}] [TOOL_DONE] {name} completed with result: {result}")

                # Send result via send_tool_response
                tool_response = types.FunctionResponse(
                    name=name,
                    response=result,
                    id=call_id
                )
                await session.send_tool_response(function_responses=[tool_response])
                logger.info(f"[{end_ts}] [TOOL_RESPONSE] Sent response for {name}")

            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
