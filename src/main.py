import asyncio
import os
import pyaudio
import sys
from google.genai import types
from src.client import SophieLiveClient
from src.auth import check_adc
from src import config

# Audio configuration
# NOTE: This script is for local CLI voice interaction using PyAudio.
# If using the web demo (server.py), do NOT run this script simultaneously
# as it will cause multiple voices/overlaps.
FORMAT = pyaudio.paInt16
CHANNELS = config.CHANNELS
IN_RATE = config.INPUT_RATE
OUT_RATE = config.OUTPUT_RATE
CHUNK = config.CHUNK_SIZE

class AudioInterface:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.in_stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=IN_RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        self.out_stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=OUT_RATE,
            output=True,
            frames_per_buffer=CHUNK
        )
        self.is_playing = False # Flag to track AI speech

    def read(self):
        # Mute mic if AI is speaking
        if self.is_playing:
            return b'\x00' * CHUNK * 2 # Return silence
        return self.in_stream.read(CHUNK, exception_on_overflow=False)

    def write(self, data):
        self.out_stream.write(data)

    def close(self):
        try:
            if self.in_stream:
                self.in_stream.stop_stream()
                self.in_stream.close()
            if self.out_stream:
                self.out_stream.stop_stream()
                self.out_stream.close()
        except:
            pass
        self.p.terminate()

async def send_audio(session, audio_interface):
    """Continuously reads from mic and sends to Gemini."""
    try:
        while True:
            data = await asyncio.to_thread(audio_interface.read)
            await session.send_realtime_input(
                audio=types.Blob(data=data, mime_type=config.INPUT_AUDIO_MIME_TYPE)
            )
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Audio send error: {e}")

async def receive_responses(session, audio_interface, client):
    """Continuously receives from Gemini and plays audio / handles tools."""
    try:
        # Loop forever to handle multiple turns
        while True:
            # session.receive() yields messages for a single turn
            async for message in session.receive():
                # 1. Handle Model Content (Audio/Text)
                if message.server_content:
                    if message.server_content.model_turn:
                        audio_interface.is_playing = True # AI started talking
                        for part in message.server_content.model_turn.parts:
                            if part.inline_data:
                                await asyncio.to_thread(audio_interface.write, part.inline_data.data)
                            if part.text:
                                print(f"Sophie: {part.text}")
                        
                        if message.server_content.turn_complete:
                            audio_interface.is_playing = False # AI finished turn
                    
                    if message.server_content.interrupted:
                        print("--- Sophie interrupted ---")
                        audio_interface.is_playing = False

                # 2. Handle Tool Calls
                if message.tool_call:
                    await client.handle_tool_call(session, message.tool_call)
            
            # Brief sleep between turn-receives
            await asyncio.sleep(0.01)
                
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Response receive error: {e}")

async def main():
    print("--- Sophie Smart Glasses AI - Real-time Voice ---")
    
    if not check_adc():
        print("Error: ADC not configured. Please run 'gcloud auth application-default login'.")
        sys.exit(1)
    
    client = SophieLiveClient()
    audio = AudioInterface()
    
    print("Connecting to Gemini Live...")
    try:
        async with await client.connect() as session:
            print("Sophie is listening. Speak now! (Ctrl+C to exit)")
            
            # Python 3.10 compatible concurrency using gather
            # wrap in a try/except to handle cancellation cleanly
            try:
                await asyncio.gather(
                    send_audio(session, audio),
                    receive_responses(session, audio, client)
                )
            except asyncio.CancelledError:
                pass
                
    except KeyboardInterrupt:
        print("\nSophie: Closing the session. See you soon!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        audio.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass