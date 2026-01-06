# Product Guide - Ajna Smart Glasses AI

## Initial Concept
A gemini live api on vertex ai based application for realtime user interaction through voice. The project overview and goals are provided in @PRD.md and the base prompt to enhance is provided in @base_prompt.md

## Target Audience
- **Tech Enthusiasts:** Early adopters looking for a cutting-edge, emotionally intelligent AI companion integrated into wearable hardware.
- **Wellness & Fitness Seekers:** Individuals looking for real-time guidance in Yoga, posture, nutrition, and mindfulness.
- **Productivity Professionals:** Users who need hands-free assistance with meetings, real-time translation, and financial habit tracking.

## Core Value Proposition
Ajna is not just an assistant; it's a playful, wise, and emotionally present friend. The application leverages the Gemini Live API to provide a seamless, voice-first experience that integrates vision and multi-modal assistance into daily life via smart glasses.

## Key Features (Hero Features)
- **Real-time Voice Interaction (Gemini Live):** Low-latency, emotionally intelligent conversations with a strict "Urban Indian" accent and persona adherence.
- **Contextual Vision ("What is this?"):** Intelligent object and scene recognition using the glasses' camera, providing immediate contextual feedback.
- **Multi-modal Role Switching:** Dynamic adaptation to various roles (Yoga Trainer, Chef, Financial Advisor, etc.) without losing the core Ajna persona.
- **Precision Tool Integration:** Highly accurate mapping of voice intent to system functions (Camera control, Music, Messaging, Payments).

## Success Metrics
- **System Instruction Adherence:** Strict compliance with the Ajna persona, language constraints, and accent rules.
- **Tool Call Accuracy:** 100% precision in invoking the correct mock tool calls based on user intent.
- **Interaction Latency:** Minimal delay in voice processing and response generation to ensure a natural conversational flow.

## Implementation Strategy
- **Enhanced Prompting:** Utilizing Gemini prompting best practices to maximize model adherence to complex system instructions.
- **Dynamic Python Mocks:** Implementing a robust mocking layer for all tool and agent calls to facilitate rapid development and testing without requiring live hardware/backend integration for every component.
