import os

# Google Cloud Settings
PROJECT_ID = "account-pocs"
LOCATION = "us-central1"

# Gemini Live Model Settings
# gemini-live-2.5-flash-native-audio is the likely ID for the latest Live API preview
MODEL_ID = "gemini-live-2.5-flash-native-audio"

# Audio Settings (PyAudio)
AUDIO_FORMAT = 16  # paInt16
CHANNELS = 1
INPUT_RATE = 16000
OUTPUT_RATE = 24000
CHUNK_SIZE = 512

# Live API Configurable Parameters
LIVE_CONFIG = {
    "voice_name": "Kore",  # Options: Aoede, Charon, Fenrir, Kore, Puck (Kore is female)
    "language_code": "en-IN",
    "audio_encoding": "LINEAR16",
    
    # VAD & Interruption Controls
    "vad_sensitivity": "NORMAL", # NORMAL, LOW, HIGH
    "silence_duration_ms": 1000,   # Silence before committing EOS (End Of Speech)
    "prefix_padding_ms": 300,      # Speech duration before committing SOS (Start Of Speech)
    "barge_in": True,              # If True, start of activity interrupts model
    
    # Proactivity
    "proactive_audio": True,       # Model can ignore out-of-context speech
}

# Persona Prompt
from src.prompts import SOPHIE_SYSTEM_INSTRUCTION
SYSTEM_INSTRUCTION = SOPHIE_SYSTEM_INSTRUCTION