# Plan: Foundation - Ajna Persona & Core Tool Mocking Framework

This plan follows the project workflow: commit after tasks and maintain 80% test coverage.

## Phase 1: Environment & Project Setup [checkpoint: f4fc76d]
- [x] Task: Initialize Python project using `uv`, install `google-genai` and `pytest`. 4b75daf
- [x] Task: Set up Application Default Credentials (ADC) local check. 68595b0
- [x] Task: Conductor - User Manual Verification 'Phase 1: Environment & Project Setup' (Protocol in workflow.md)

## Phase 2: Core Mocking Framework [checkpoint: ad66bfc]
- [x] Task: Create a base \`ToolHandler\` class and implement mocks for \`capture_frame\`, \`call_someone\`, and \`play_music\`. 4e83349
- [x] Task: Implement unit tests for mock handlers ensuring they return the expected JSON structures. 08fe07b
- [x] Task: Conductor - User Manual Verification 'Phase 2: Core Mocking Framework' (Protocol in workflow.md)

## Phase 3: Enhanced Prompting & Persona Implementation [checkpoint: 727edde]
- [x] Task: Draft the enhanced system instructions (Persona + System Rules) in a Python module. 4c151ab
- [x] Task: Integrate the `google-genai` client with the enhanced prompt and tool definitions. cb75dac
- [x] Task: Implement a CLI-based interaction loop to test voice/text input against the mock tools. 7c36acc
- [x] Task: Conductor - User Manual Verification 'Phase 3: Enhanced Prompting & Persona Implementation' (Protocol in workflow.md)

## Phase 4: Verification & Checkpointing [checkpoint: ef3b50c]
- [x] Task: Run integration tests to verify that specific user intents (e.g., "What is this?") correctly trigger the mock `capture_frame` tool. 0fce466
- [x] Task: Verify persona adherence (No "I am an AI", strict English) via a suite of test prompts. d370339
- [x] Task: Conductor - User Manual Verification 'Phase 4: Verification & Checkpointing' (Protocol in workflow.md)
