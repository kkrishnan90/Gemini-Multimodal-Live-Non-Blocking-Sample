# Sophie Assistant - Gemini Multimodal Live API Demo

This project demonstrates a real-time, multimodal AI assistant named "Sophie," built using the **Google Gemini Multimodal Live API**. It features a Python backend that handles the connection to Gemini and a React frontend for the user interface.

## 🚀 Key Features

*   **Real-time Multimodal Interaction:** Talk to Sophie using voice and video.
*   **Dynamic Persona Updates:** Change Sophie's behavior and instructions on the fly without restarting the session.
*   **Tool Use:** Sophie can execute defined tools (mocked in this demo) like "taking a photo," "searching Google," or "logging a meal."
*   **Dual-Stack Architecture:** Python (FastAPI/WebSockets) backend + React (Vite) frontend.

---

## 🛠️ Prerequisites

*   **Python 3.10+**
*   **Node.js 18+**
*   **`uv`** (Python package manager): [Installation Guide](https://github.com/astral-sh/uv)
*   **Google Cloud Project** with Vertex AI API enabled.
*   **Application Default Credentials (ADC)** configured locally.

---

## ⚙️ Setup & Installation

### 1. Backend Setup

The backend handles the WebSocket connection to the frontend and the secure connection to the Gemini Live API.

1.  **Navigate to the project root:**
    ```bash
    cd /path/to/sophie-assistant
    ```

2.  **Install dependencies using `uv`:**
    This will create a virtual environment (`.venv`) and install all required packages from `pyproject.toml`.
    ```bash
    uv sync
    ```

3.  **Start the Backend Server:**
    You can use the provided helper script:
    ```bash
    ./start_backend.sh
    ```
    *Or run manually:*
    ```bash
    source .venv/bin/activate
    python main.py
    ```
    The backend will run on `http://localhost:8000`.

### 2. Frontend Setup

The frontend provides the user interface to interact with Sophie.

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install Node dependencies:**
    ```bash
    npm install
    ```

3.  **Start the Development Server:**
    ```bash
    npm run dev
    ```
    The frontend will typically run on `http://localhost:5173`. Open this URL in your browser.

---

## 🧠 How the Persona Update Works

One of the most powerful features of this demo is the ability to update "Sophie's" persona or system instructions dynamically *during* an active live session.

### Technical Implementation: `send_client_content` & Session State

The Gemini Multimodal Live API maintains the conversation state **server-side**. Unlike standard REST APIs where you must re-send history, the Live API accumulates context throughout the WebSocket session.

#### The `send_client_content` Mechanism

When `update_persona` is called, the `google-genai` SDK performs the following:

1.  **Message Serialization:** It packages the instruction into a JSON object for the WebSocket.
2.  **WebSocket Transmission:** The message is sent over the active Bidi (bidirectional) stream to the Gemini server using the `send_client_content` method.
3.  **Context Append:** The API server receives this and **appends** the new `turns` to the existing session history.
4.  **Role Processing:** By setting the `role` to `"system"`, the instruction is injected as a system-level directive within the chronological context.

#### Factual Behavior
*   **Additive, Not Destructive:** The `send_client_content` message does not trigger a session reset. It does not overwrite the initial `system_instruction` provided during the `setup` phase.
*   **In-Order Processing:** As confirmed by the SDK source code, any new content you send via `send_client_content` is strictly appended to the end of the current session's history. It doesn't magically slot in at the beginning or replace what's there; it just becomes the next "turn" in the conversation.
*   **Model Attention:** The model processes the accumulated context window. When a new turn with `role: "system"` appears late in the history, the transformer's attention mechanism naturally prioritizes these recent tokens as the most immediate constraints for subsequent generation.

#### Context Example
If you update the persona mid-session, the server-side conversation history effectively looks like this:

```json
[
  { "role": "system", "text": "You are a helpful assistant." },
  { "role": "user",   "text": "Hello!" },
  { "role": "model",  "text": "Hi there! How can I help?" },
  { "role": "system", "text": "IMPORTANT: You are now a pirate." }  <-- The update is appended here
]
```
The model's next response will now generate based on this full sequence, prioritizing the "pirate" instruction because it is the most recent system directive.

This implementation allows for "Hot-Swapping" assistant behavior with sub-second latency, as it avoids the overhead of establishing a new connection or re-initializing the model state.

---

## 📂 Project Structure

*   **`src/`**: Python backend source code.
    *   `client.py`: Handles Gemini Live API connection and logic (including `update_persona`).
    *   `server.py`: FastAPI server and WebSocket handling.
    *   `tools.py`: Definitions of tools Sophie can use.
    *   `config.py`: Configuration constants (Model ID, Project ID, etc.).
*   **`frontend/`**: React application source code.
*   **`main.py`**: Entry point for the backend application.
*   **`conductor/`**: Project documentation and track management (internal use).

## 🐛 Troubleshooting

*   **Audio/Video Issues:** Ensure your browser has permission to access the microphone and camera.
*   **Connection Errors:** Check that the backend is running and the port (8000) is not blocked.
*   **Authentication:** Ensure you have the correct Google Cloud permissions and `GOOGLE_APPLICATION_CREDENTIALS` environment variable set if not using the default user login.
