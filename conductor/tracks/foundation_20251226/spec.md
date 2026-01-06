# Specification: Foundation - Ajna Persona & Core Tool Mocking Framework

## Overview
This track establishes the foundational logic for the Ajna Smart Glasses AI. It focuses on the primary persona constraints (Urban Indian accent, English-only, playful/wise tone) and the core mechanism for handling tool calls via a robust mocking layer.

## Requirements
- **Persona Adherence:** Enhanced system instructions must ensure strict adherence to the "Ajna" persona across all interactions.
- **Language/Accent Control:** Strict English-only output with an Urban Indian accent.
- **Tool Mocking Framework:** A modular Python system to handle function calls and return pre-defined or dynamic mock responses.
- **Mocked Tools (Phase 1):**
    - `capture_frame`: Returns mock scene descriptions.
    - `call_someone`: Simulates contact resolution and confirmation flow.
    - `play_music`: Simulates playback start.
    - `get_current_date_and_time`: Returns system time.

## Technical Constraints
- Model: `gemini-2.5-flash-native-audio` on Vertex AI.
- SDK: `google-genai`.
- Mocking: Python `unittest.mock` and custom class-based handlers.
