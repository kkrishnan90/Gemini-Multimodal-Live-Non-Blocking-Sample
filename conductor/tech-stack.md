# Tech Stack - Ajna Smart Glasses AI

## Core AI Platform
- **Model:** `gemini-2.5-flash-native-audio` (Optimized for low-latency voice interaction and high instruction adherence).
- **Platform:** Vertex AI (Enterprise-grade GenAI platform).
- **Primary SDK:** `google-genai` (Unified Python SDK for Google Generative AI).

## Backend & Logic
- **Language:** Python 3.* (Primary language for prompt orchestration, tool logic, and mocking).
- **Package Manager:** `uv` (Fast dependency management and virtual environment handling).

## Tooling & Mocking Layer
- **Mocking Strategy:** 
  - **`unittest.mock`:** For unit-level simulation of external services and system calls.
  - **Custom Tool Handlers:** A modular architecture of Python classes to simulate real-world tool behavior (Camera, GPS, Music Player, Scanner) and return structured JSON responses.
- **Environment Management:** Virtual environments managed via `uv`.

## Integration & Communication
- **Architecture:** Tool-First approach where the LLM orchestrates actions via function calling.
- **Security:** Leveraging Application Default Credentials (ADC) for secure access to Vertex AI resources.
- **Reference Base:** Leveraging patterns from `kkrishnan90/gemini-mm-live-demo` for foundation and best practices.

## Success Criteria (Technical)
- **Model Adherence:** Validated against the Ajna persona and Urban Indian accent constraints.
- **Mock Reliability:** 100% predictable tool responses for all defined functionality in the PRD.
- **Latency:** Optimized SDK usage and minimal overhead in the tool/mock execution path.
