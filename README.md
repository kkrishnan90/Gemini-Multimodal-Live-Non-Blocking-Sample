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

### The Logic (`send_client_content`)

In a standard interaction, "System Instructions" are usually set once at the beginning of a session (in the `connect` config). However, the Gemini Live API allows you to inject new system-level instructions into the conversation history at any point using `client_content` messages.

This is implemented in `src/client.py` within the `SophieLiveClient` class:

```python
async def update_persona(self, session, instruction):
    """Updates the system instruction dynamically."""
    print(f"--- Sending Client Content (Update Persona): {instruction[:50]}... ---")
    
    # We construct a 'Content' object with the role set to "system".
    # This effectively appends a new system turn to the conversation history.
    await session.send_client_content(
        turns=[types.Content(
            role="system",
            parts=[types.Part(text=instruction)]
        )],
        turn_complete=True
    )
    print("--- Persona Update Sent Successfully ---")
```

### Flow of Events

1.  **User Action:** On the frontend, the user selects a new mode or updates a text field (e.g., "Be a sarcastic pirate").
2.  **WebSocket Message:** The frontend sends this new instruction string to the Python backend via the established WebSocket.
3.  **Backend Processing:** The backend receives the message and calls `client.update_persona(session, new_instruction)`.
4.  **API Call (`send_client_content`):**
    *   The `send_client_content` method is invoked on the active Gemini Live session.
    *   It sends a `Content` object where `role="system"`.
    *   **Crucially**, this message is **added** to the conversation history (context window); it does not delete or replace the initial system instructions.
5.  **Effective Update:** Because LLMs prioritize the most recent instructions in their context, the model effectively adopts this new persona immediately. The next response will reflect these new constraints or personality traits, treating them as the current active directive.

This allows for highly dynamic interactions where the assistant's personality, constraints, or knowledge base scope can shift contextually without breaking the audio/video connection.

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
