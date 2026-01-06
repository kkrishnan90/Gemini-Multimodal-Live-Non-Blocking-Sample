import asyncio
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google.genai import types
from src.client import SophieLiveClient
from src.auth import check_adc
import base64

app = FastAPI()

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sophie-server")

@app.websocket("/ws/live")
async def live_proxy(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected via WebSocket")
    
    if not check_adc():
        await websocket.send_json({"error": "ADC not configured"})
        await websocket.close()
        return

    client = SophieLiveClient()
    
    try:
        async with await client.connect() as session:
            logger.info("Connected to Gemini Live")
            
            async def send_to_gemini():
                """Forward audio from browser to Gemini."""
                try:
                    while True:
                        message = await websocket.receive()
                        if "bytes" in message:
                            # Direct binary audio
                            await session.send_realtime_input(
                                audio=types.Blob(data=message["bytes"], mime_type="audio/pcm;rate=16000")
                            )
                        elif "text" in message:
                            # Handle potential control messages from UI
                            try:
                                data = json.loads(message["text"])
                                if data.get("type") == "end":
                                    break
                                elif data.get("type") == "update_persona":
                                    instruction = data.get("instruction")
                                    if instruction:
                                        logger.info(f"Updating persona to: {instruction[:50]}...")
                                        await client.update_persona(session, instruction)
                                        # Send confirmation to frontend to display in Tool Executions
                                        await websocket.send_json({
                                            "type": "tool_call",
                                            "name": "system_instruction_update",
                                            "args": {"instruction": instruction[:100] + "..."}
                                        })
                            except json.JSONDecodeError:
                                pass
                except Exception as e:
                    logger.error(f"Error forwarding to Gemini: {e}")

            async def receive_from_gemini():
                """Forward responses from Gemini to browser."""
                try:
                    while True:
                        # session.receive() yields messages for one complete turn
                        async for message in session.receive():
                            # Handle Server Content (Audio and Text)
                            if message.server_content:
                                response_payload = {"type": "server_content"}
                                if message.server_content.model_turn:
                                    parts = []
                                    for part in message.server_content.model_turn.parts:
                                        if part.inline_data:
                                            parts.append({
                                                "audio": base64.b64encode(part.inline_data.data).decode("utf-8")
                                            })
                                        if part.text:
                                            parts.append({"text": part.text})
                                    response_payload["parts"] = parts
                                
                                if message.server_content.turn_complete:
                                    response_payload["turn_complete"] = True
                                
                                if message.server_content.interrupted:
                                    response_payload["interrupted"] = True
                                
                                # Add Transcription Support
                                if message.server_content.input_transcription and message.server_content.input_transcription.text:
                                    logger.info(f"Input Transcription: {repr(message.server_content.input_transcription.text)}")
                                    response_payload["input_transcription"] = {
                                        "text": message.server_content.input_transcription.text,
                                        "finished": message.server_content.input_transcription.finished
                                    }
                                if message.server_content.output_transcription and message.server_content.output_transcription.text:
                                    logger.info(f"Output Transcription: {repr(message.server_content.output_transcription.text)}")
                                    response_payload["output_transcription"] = {
                                        "text": message.server_content.output_transcription.text,
                                        "finished": message.server_content.output_transcription.finished
                                    }
                                
                                await websocket.send_json(response_payload)

                            # Handle Tool Calls
                            if message.tool_call:
                                logger.info(f"Tool call: {message.tool_call}")
                                await websocket.send_json({
                                    "type": "tool_call",
                                    "name": message.tool_call.function_calls[0].name,
                                    "args": message.tool_call.function_calls[0].args
                                })
                                await client.handle_tool_call(session, message.tool_call)
                        
                        # Brief sleep to allow other tasks to process
                        await asyncio.sleep(0.01)
                except Exception as e:
                    logger.error(f"Error receiving from Gemini: {e}")

            # Run loops
            await asyncio.gather(send_to_gemini(), receive_from_gemini())

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Server error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)