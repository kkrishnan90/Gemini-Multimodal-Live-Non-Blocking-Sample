import os
from enum import Enum
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class AuthMode(str, Enum):
    """Authentication mode for Gemini API access."""
    AI_STUDIO = "AI_STUDIO"
    VERTEX_AI = "VERTEX_AI"


# Authentication Configuration
AUTH_MODE = AuthMode(os.getenv("AUTH_MODE", "VERTEX_AI"))

# AI Studio Configuration (API Key)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Vertex AI Configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "account-pocs")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# Gemini Live Model Settings
# AI Studio and Vertex AI use different model IDs
MODEL_ID_AI_STUDIO = os.getenv(
    "MODEL_ID_AI_STUDIO", "gemini-2.5-flash-native-audio-preview-12-2025"
)
MODEL_ID_VERTEX_AI = os.getenv(
    "MODEL_ID_VERTEX_AI", "gemini-live-2.5-flash-native-audio"
)

# Legacy MODEL_ID for backward compatibility
MODEL_ID = os.getenv("MODEL_ID", MODEL_ID_VERTEX_AI)

# Audio Settings (PyAudio)
AUDIO_FORMAT = 16  # paInt16
CHANNELS = 1
INPUT_RATE = 16000
OUTPUT_RATE = 24000
CHUNK_SIZE = 512


def _parse_bool(value: str) -> bool:
    """Parse boolean from environment variable string."""
    return value.lower() in ("true", "1", "yes")


# Live API Configurable Parameters
LIVE_CONFIG = {
    "voice_name": os.getenv("VOICE_NAME", "Kore"),
    "language_code": os.getenv("LANGUAGE_CODE", "en-IN"),
    "audio_encoding": "LINEAR16",

    # VAD & Interruption Controls
    "vad_sensitivity": os.getenv("VAD_SENSITIVITY", "NORMAL"),
    "silence_duration_ms": int(os.getenv("SILENCE_DURATION_MS", "1000")),
    "prefix_padding_ms": int(os.getenv("PREFIX_PADDING_MS", "300")),
    "barge_in": _parse_bool(os.getenv("BARGE_IN", "true")),

    # Proactivity
    "proactive_audio": _parse_bool(os.getenv("PROACTIVE_AUDIO", "true")),
}

# Persona Prompt
from src.prompts import SOPHIE_SYSTEM_INSTRUCTION
SYSTEM_INSTRUCTION = SOPHIE_SYSTEM_INSTRUCTION


def validate_config() -> None:
    """Validate configuration based on selected auth mode."""
    if AUTH_MODE == AuthMode.AI_STUDIO:
        if not GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY is required when AUTH_MODE=AI_STUDIO. "
                "Get your API key from: https://aistudio.google.com/apikey"
            )
    elif AUTH_MODE == AuthMode.VERTEX_AI:
        if PROJECT_ID == "your-project-id":
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT must be set when AUTH_MODE=VERTEX_AI. "
                "Also ensure ADC is configured: gcloud auth application-default login"
            )
