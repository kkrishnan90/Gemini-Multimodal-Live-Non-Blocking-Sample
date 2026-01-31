# Gemini Multimodal Live Non-Blocking Sample

A real-time multimodal AI assistant using the **Gemini Multimodal Live API** with support for **non-blocking function calls**. Features a Python/FastAPI backend with WebSocket streaming and a React/Vite frontend.

## Project Structure

```
.
├── src/                          # Backend Python source code
│   ├── server.py                 # FastAPI WebSocket server (entry point)
│   ├── client.py                 # Gemini Live API client wrapper
│   ├── tools.py                  # Tool implementations (function handlers)
│   ├── config.py                 # Configuration and environment variables
│   ├── prompts.py                # System instruction / persona prompt
│   └── auth.py                   # Authentication helpers
│
├── frontend/                     # React frontend
│   ├── src/
│   │   ├── App.tsx               # Main React component (WebSocket + Audio)
│   │   └── main.tsx              # React entry point
│   ├── package.json
│   └── vite.config.ts
│
├── tests/                        # Test files
│   ├── test_tools.py             # Tool handler tests
│   ├── test_client.py            # Client tests
│   └── ...
│
├── start.sh                      # Script to start both backend and frontend
├── pyproject.toml                # Python dependencies (uv)
└── .env.example                  # Environment variable template
```

## Core Files Explained

### Backend (`src/`)

| File | Purpose |
|------|---------|
| `server.py` | FastAPI app with WebSocket endpoint `/ws/live`. Proxies audio between browser and Gemini. Handles auth config API (`/api/auth/config`). |
| `client.py` | `SophieLiveClient` class - manages Gemini Live API connection, tool definitions, and tool call handling. |
| `tools.py` | `ToolHandler` class - contains the actual tool implementations that get executed when Gemini calls a function. |
| `config.py` | All configuration: auth mode, model IDs, audio settings, VAD parameters. Loads from `.env`. |
| `prompts.py` | System instruction that defines the AI persona and tool usage rules. |

### Frontend (`frontend/`)

| File | Purpose |
|------|---------|
| `App.tsx` | Single-page React app handling microphone capture, WebSocket connection, audio playback, and UI. |

---

## Tool Call Flow

This is how function calling works in this project:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TOOL CALL FLOW                                 │
└─────────────────────────────────────────────────────────────────────────────┘

1. TOOL DEFINITION (src/client.py:105-153)
   └── _get_tools_definitions() creates FunctionDeclaration objects
       └── Includes: name, description, parameters schema
       └── For AI Studio: adds behavior: NON_BLOCKING

2. SESSION SETUP (src/client.py:155-225)
   └── connect() passes tools to LiveConnectConfig
       └── Tools are registered with the Gemini model

3. TOOL INVOCATION (src/server.py:277-296)
   └── When Gemini calls a tool, server receives message.tool_call
       └── Logs: [TOOL] tool_name(args)
       └── Calls: client.handle_tool_call(session, message.tool_call)

4. TOOL EXECUTION (src/client.py:227-273)
   └── handle_tool_call() looks up handler in tools_map
       └── tools_map maps "get_lucky_number" → tool_handler.get_lucky_number
       └── Executes the async handler with args
       └── Sends FunctionResponse back via session.send_tool_response()

5. TOOL IMPLEMENTATION (src/tools.py)
   └── ToolHandler class contains the actual functions:
       └── get_current_date_and_time() - returns current date/time
       └── get_lucky_number() - returns lucky number (10s delay to demo non-blocking)
       └── action_trigger(issue_type) - routes issues
```

### Adding a New Tool

1. **Define the handler** in `src/tools.py`:
```python
async def my_new_tool(self, param1: str) -> dict:
    # Your implementation
    return {"result": "value"}
```

2. **Add function declaration** in `src/client.py` → `_get_tools_definitions()`:
```python
{
    "name": "my_new_tool",
    "description": "What this tool does",
    "parameters": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "Parameter description"}
        },
        "required": ["param1"]
    }
}
```

3. **Register in tools_map** in `src/client.py` → `__init__()`:
```python
self.tools_map = {
    ...
    "my_new_tool": self.tool_handler.my_new_tool,
}
```

---

## Non-Blocking Function Calls (AI Studio Only)

When using AI Studio mode, function calls support **asynchronous execution**, allowing the model to continue speaking while waiting for tool results.

### How It Works

1. **Tool declarations** automatically include `behavior: NON_BLOCKING` (line 142-144 in `client.py`)

2. **The model can speak** while the tool executes (e.g., "Let me check that for you...")

3. **When the result arrives**, the model incorporates it naturally

### Example: `get_lucky_number`

This tool has a 10-second delay to demonstrate non-blocking behavior:
- User: "Give me a lucky number"
- Model: Calls `get_lucky_number`, continues talking
- (10 seconds later) Tool returns result
- Model: "Your lucky number is 42!"

> **Note**: Non-blocking is NOT supported on Vertex AI.

---

## Authentication Modes

| Mode | Configuration | Use Case |
|------|---------------|----------|
| `AI_STUDIO` | `GOOGLE_API_KEY` env var | Development, prototyping, non-blocking support |
| `VERTEX_AI` | ADC + `GOOGLE_CLOUD_PROJECT` | Production, enterprise |

Set via `AUTH_MODE` environment variable or runtime API.

---

## Quick Start

### 1. Install Dependencies

```bash
# Backend (Python)
uv sync

# Frontend (Node.js)
cd frontend && npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

**For AI Studio:**
```env
AUTH_MODE=AI_STUDIO
GOOGLE_API_KEY=your-api-key-here
```

**For Vertex AI:**
```env
AUTH_MODE=VERTEX_AI
GOOGLE_CLOUD_PROJECT=your-project-id
```

### 3. Run

```bash
# Start both backend and frontend
./start.sh

# Or separately:
# Backend: uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload
# Frontend: cd frontend && npm run dev
```

Open http://localhost:5173 in your browser.

---

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_MODE` | `VERTEX_AI` | `AI_STUDIO` or `VERTEX_AI` |
| `GOOGLE_API_KEY` | - | API key for AI Studio mode |
| `GOOGLE_CLOUD_PROJECT` | - | GCP project for Vertex AI |
| `MODEL_ID_AI_STUDIO` | `gemini-2.5-flash-native-audio-preview-12-2025` | Model for AI Studio |
| `MODEL_ID_VERTEX_AI` | `gemini-live-2.5-flash-preview-native-audio-09-2025` | Model for Vertex AI |
| `VOICE_NAME` | `Kore` | TTS voice name |
| `SILENCE_DURATION_MS` | `600` | Silence before end-of-speech |
| `BARGE_IN` | `true` | Allow user interruption |

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ws/live` | WebSocket | Main audio streaming endpoint |
| `/api/auth/config` | GET | Get current auth configuration |
| `/api/auth/config` | POST | Update auth configuration |

---

## Testing

```bash
# Run all tests
source .venv/bin/activate && pytest

# Run specific test
pytest tests/test_tools.py

# With coverage
pytest --cov=src
```
