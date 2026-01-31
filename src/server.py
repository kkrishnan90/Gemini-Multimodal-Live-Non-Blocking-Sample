import asyncio
import json
import logging
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.genai import types
from websockets.exceptions import ConnectionClosed
from src.client import SophieLiveClient
from src.auth import check_adc
from src.config import AuthMode
import src.config as config
import base64

app = FastAPI()


class AuthConfig(BaseModel):
    """Request model for authentication configuration."""
    auth_mode: str
    api_key: Optional[str] = None
    project_id: Optional[str] = None
    location: Optional[str] = None


class AuthConfigResponse(BaseModel):
    """Response model for authentication configuration."""
    auth_mode: str
    project_id: str
    location: str
    has_api_key: bool

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sophie-server")
logger.setLevel(logging.DEBUG)


# Runtime auth configuration (can be updated via API)
_runtime_auth_config = {
    "auth_mode": config.AUTH_MODE,
    "api_key": config.GOOGLE_API_KEY,
    "project_id": config.PROJECT_ID,
    "location": config.LOCATION,
}


@app.get("/api/auth/config", response_model=AuthConfigResponse)
async def get_auth_config():
    """Get current authentication configuration."""
    return AuthConfigResponse(
        auth_mode=_runtime_auth_config["auth_mode"].value,
        project_id=_runtime_auth_config["project_id"],
        location=_runtime_auth_config["location"],
        has_api_key=bool(_runtime_auth_config["api_key"]),
    )


@app.post("/api/auth/config", response_model=AuthConfigResponse)
async def set_auth_config(auth_config: AuthConfig):
    """Update authentication configuration at runtime."""
    logger.info(f"Received auth config update: auth_mode={auth_config.auth_mode}, "
                f"api_key_provided={auth_config.api_key is not None and len(auth_config.api_key or '') > 0}, "
                f"project_id={auth_config.project_id}, location={auth_config.location}")

    try:
        _runtime_auth_config["auth_mode"] = AuthMode(auth_config.auth_mode)
    except ValueError:
        _runtime_auth_config["auth_mode"] = AuthMode.VERTEX_AI

    # Only update api_key if a non-empty value is provided
    # This preserves the existing API key from .env if user doesn't enter a new one
    if auth_config.api_key and len(auth_config.api_key) > 0:
        _runtime_auth_config["api_key"] = auth_config.api_key
        logger.info(f"API key updated, length={len(auth_config.api_key)}")
    else:
        logger.info(f"API key not provided in request, keeping existing: {bool(_runtime_auth_config['api_key'])}")
    if auth_config.project_id is not None:
        _runtime_auth_config["project_id"] = auth_config.project_id
    if auth_config.location is not None:
        _runtime_auth_config["location"] = auth_config.location

    logger.info(f"Auth config updated: mode={_runtime_auth_config['auth_mode'].value}, "
                f"has_api_key={bool(_runtime_auth_config['api_key'])}")
    return AuthConfigResponse(
        auth_mode=_runtime_auth_config["auth_mode"].value,
        project_id=_runtime_auth_config["project_id"],
        location=_runtime_auth_config["location"],
        has_api_key=bool(_runtime_auth_config["api_key"]),
    )


@app.websocket("/ws/live")
async def live_proxy(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected via WebSocket")

    # Get current auth configuration
    auth_mode = _runtime_auth_config["auth_mode"]
    api_key = _runtime_auth_config["api_key"]
    project_id = _runtime_auth_config["project_id"]
    location = _runtime_auth_config["location"]

    # # Log auth configuration for debugging
    # logger.info(f"Auth mode: {auth_mode.value}")
    # logger.info(f"API key present: {bool(api_key)}, length: {len(api_key) if api_key else 0}")
    # logger.info(f"Project ID: {project_id}, Location: {location}")

    # Validate auth configuration based on mode
    if auth_mode == AuthMode.AI_STUDIO:
        if not api_key:
            logger.error("AI Studio mode but no API key configured")
            await websocket.send_json({
                "error": "API key not configured. Please set your API key in Settings."
            })
            await websocket.close()
            return
    else:  # VERTEX_AI
        if not check_adc():
            logger.error("Vertex AI mode but ADC not configured")
            await websocket.send_json({
                "error": "ADC not configured. Run: gcloud auth application-default login"
            })
            await websocket.close()
            return

    # Create client with runtime auth configuration
    # logger.info(f"Creating client with auth_mode={auth_mode.value}")
    try:
        client = SophieLiveClient(
            auth_mode=auth_mode,
            api_key=api_key,
            project_id=project_id,
            location=location,
        )
        # logger.info(f"Client created successfully, model_id={client.model_id}")
    except Exception as e:
        logger.error(f"Failed to create client: {e}", exc_info=True)
        await websocket.send_json({"error": f"Failed to create client: {e}"})
        await websocket.close()
        return

    try:
        # logger.info(f"Connecting to Gemini Live with model={client.model_id}")
        async with await client.connect() as session:
            # logger.info("Connected to Gemini Live successfully")

            # Send session info to frontend
            session_id = getattr(session, 'session_id', None) or id(session)
            await websocket.send_json({
                "type": "session_started",
                "session_id": str(session_id),
                "model_id": client.model_id,
                "auth_mode": client.auth_mode.value
            })
            logger.info(f"Session started: {session_id}")

            audio_chunks_sent = 0

            async def send_to_gemini():
                """Forward audio from browser to Gemini."""
                nonlocal audio_chunks_sent
                try:
                    while True:
                        message = await websocket.receive()
                        if "bytes" in message:
                            # Direct binary audio
                            audio_bytes = message["bytes"]
                            audio_chunks_sent += 1

                            # # Check if audio has actual content (not silent)
                            # if audio_chunks_sent <= 5 or audio_chunks_sent % 100 == 0:
                            #     # Calculate RMS to detect if audio has content
                            #     import struct
                            #     samples = struct.unpack(f'<{len(audio_bytes)//2}h', audio_bytes)
                            #     rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
                            #     logger.info(f"Audio chunk #{audio_chunks_sent}: size={len(audio_bytes)} bytes, samples={len(samples)}, RMS={rms:.1f}")

                            await session.send_realtime_input(
                                audio=types.Blob(data=audio_bytes, mime_type=config.INPUT_AUDIO_MIME_TYPE)
                            )
                        elif "text" in message:
                            # Handle potential control messages from UI
                            try:
                                data = json.loads(message["text"])
                                if data.get("type") == "end":
                                    break
                            except json.JSONDecodeError:
                                pass
                except Exception as e:
                    logger.error(f"Error forwarding to Gemini: {e}")

            async def receive_from_gemini():
                """Forward responses from Gemini to browser."""
                # logger.info("receive_from_gemini started, waiting for messages...")
                try:
                    while True:
                        # session.receive() yields messages for one complete turn
                        async for message in session.receive():
                            # # Log raw message structure for debugging
                            # sc = message.server_content
                            # has_model_turn = sc and sc.model_turn is not None
                            # has_parts = has_model_turn and sc.model_turn.parts is not None
                            # num_parts = len(sc.model_turn.parts) if has_parts else 0
                            # has_input_trans = sc and sc.input_transcription is not None
                            # has_output_trans = sc and sc.output_transcription is not None
                            # logger.info(f"Received: model_turn={has_model_turn}, parts={num_parts}, in_trans={has_input_trans}, out_trans={has_output_trans}")
                            # Handle Server Content (Audio and Text)
                            if message.server_content:
                                response_payload = {"type": "server_content"}
                                if message.server_content.model_turn:
                                    mt = message.server_content.model_turn
                                    # logger.debug(f"model_turn.parts type={type(mt.parts)}, value={mt.parts}")
                                    parts = []
                                    if mt.parts:
                                        for idx, part in enumerate(mt.parts):
                                            # logger.debug(f"Part {idx}: inline_data={part.inline_data is not None}, text={part.text is not None}, thought={part.thought}")
                                            if part.inline_data and part.inline_data.data:
                                                audio_bytes = part.inline_data.data
                                                # logger.info(f"Got audio from Gemini: {len(audio_bytes)} bytes, type={type(audio_bytes).__name__}, mime={part.inline_data.mime_type}")
                                                parts.append({
                                                    "audio": base64.b64encode(audio_bytes).decode("utf-8")
                                                })
                                            if part.text:
                                                # Skip thinking text (internal reasoning)
                                                if part.thought:
                                                    pass  # logger.debug(f"Skipping thought text: {part.text[:50]}...")
                                                else:
                                                    # logger.debug(f"Got text from Gemini: {part.text[:50]}...")
                                                    parts.append({"text": part.text})
                                    if parts:
                                        response_payload["parts"] = parts
                                    # else:
                                    #     logger.debug("model_turn has no inline_data or text parts")

                                if message.server_content.turn_complete:
                                    response_payload["turn_complete"] = True
                                    # logger.info("Turn complete received")

                                if message.server_content.interrupted:
                                    response_payload["interrupted"] = True
                                    logger.info(">>> Model response was INTERRUPTED by user speech <<<")

                                # Add Transcription Support - log all transcriptions with timestamps
                                import time
                                from datetime import datetime
                                if message.server_content.input_transcription:
                                    text = (message.server_content.input_transcription.text or "").strip()
                                    if text:
                                        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                                        logger.info(f"[{ts}] [USER] {text}")
                                    response_payload["input_transcription"] = {
                                        "text": message.server_content.input_transcription.text,
                                        "finished": message.server_content.input_transcription.finished
                                    }
                                if message.server_content.output_transcription:
                                    text = (message.server_content.output_transcription.text or "").strip()
                                    if text:
                                        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                                        logger.info(f"[{ts}] [MODEL] {text}")
                                    response_payload["output_transcription"] = {
                                        "text": message.server_content.output_transcription.text,
                                        "finished": message.server_content.output_transcription.finished
                                    }

                                await websocket.send_json(response_payload)

                            # Handle Tool Calls
                            if message.tool_call:
                                from datetime import datetime
                                tool_name = message.tool_call.function_calls[0].name
                                tool_args = message.tool_call.function_calls[0].args
                                ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                                logger.info(f"[{ts}] [TOOL] {tool_name}({tool_args})")
                                await websocket.send_json({
                                    "type": "tool_call",
                                    "name": tool_name,
                                    "args": tool_args
                                })

                                # Send interim response notification
                                await websocket.send_json({
                                    "type": "interim_response",
                                    "tool_name": tool_name,
                                    "message": f"Sending interim response for {tool_name}..."
                                })

                                await client.handle_tool_call(session, message.tool_call)

                        # Brief sleep to allow other tasks to process
                        await asyncio.sleep(0.01)
                except ConnectionClosed as e:
                    logger.error(f"Gemini connection closed during receive: code={e.code}, reason={e.reason}")
                    raise  # Re-raise to be handled by outer exception handler
                except Exception as e:
                    logger.error(f"Error receiving from Gemini: {e}")

            # Run loops
            await asyncio.gather(send_to_gemini(), receive_from_gemini())

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except ConnectionClosed as e:
        logger.error(f"Gemini WebSocket closed: code={e.code}, reason={e.reason}")
        try:
            await websocket.send_json({
                "error": f"Gemini connection closed: {e.reason or 'Unknown reason'}"
            })
        except:
            pass
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)