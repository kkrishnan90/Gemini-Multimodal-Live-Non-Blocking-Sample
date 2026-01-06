import datetime

class ToolHandler:
    """
    Handles all tool calls and returns mock responses for the Sophie Smart Glasses.
    Aligned with @base_prompt.md definitions.
    """

    # --- 1) Camera & Video ---
    def close_camera(self) -> dict:
        """Trigger: User asks to close/stop camera or when exiting a non-live camera UI."""
        return {"status": "success", "message": "Camera closed successfully."}

    def take_photo(self) -> dict:
        """Trigger: User asks to 'take a photo/snap/click now.'"""
        return {"status": "success", "message": "Snapshot captured and saved to gallery."}

    def start_video(self) -> dict:
        """Trigger: User asks to 'start recording' / 'record video.'"""
        return {"status": "success", "message": "Video recording started."}

    def stop_video(self) -> dict:
        """Trigger: User asks to stop recording / 'stop video.'"""
        return {"status": "success", "message": "Video recording stopped and saved."}

    # --- 2) Modes / App Control ---
    def stop_b(self) -> dict:
        """Trigger: 'Hey B, Stop', 'Stop B', 'end session' or equivalent."""
        return {"status": "session_ended", "message": "Sophie session ended. Goodbye!"}

    def start_observe_mode(self) -> dict:
        """Trigger: 'Start observing,' 'activate live mode,' 'start live ai,' etc."""
        return {"status": "active", "message": "Observe mode activated. I'm watching now."}

    def stop_observe_mode(self) -> dict:
        """Trigger: 'Stop observing,' 'end live mode,' etc."""
        return {"status": "inactive", "message": "Observe mode deactivated."}

    def start_translation_mode(self) -> dict:
        """Hard Trigger: strictly says 'Start translation'."""
        return {"status": "active", "message": "Translation mode started. How can I help you translate?"}

    def start_meeting_mode(self) -> dict:
        """Trigger: 'Record meeting'."""
        return {"status": "active", "message": "Meeting mode started. I'm recording and taking notes."}

    def get_current_date_and_time(self) -> dict:
        """Trigger: User asks for date, time, or variations."""
        now = datetime.datetime.now()
        return {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timezone": "IST",
            "message": f"It's currently {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d, %Y')}."
        }

    # --- 3) Music ---
    def play_music(self, action: str = "play", song_name: str = None) -> dict:
        """Trigger: 'Play music / Play <song name>.'"""
        track = song_name or "a curated playlist for you"
        return {
            "status": "playing",
            "track": track,
            "message": f"Sure, playing {track}."
        }

    # --- 4) Vision / Frame Capture ---
    def capture_frame(self, user_query: str) -> dict:
        """Hard Trigger (when NOT observing): 'What is this?'."""
        return {
            "scene_description": f"I see an interesting object related to '{user_query}'. It looks like a high-quality product.",
            "timestamp": datetime.datetime.now().isoformat(),
            "message": "Analyzing the frame now..."
        }

    # --- 5) Meal Logging ---
    def log_my_meal(self) -> dict:
        """Hard Trigger: strictly says 'Log my Meal'."""
        return {"status": "camera_open", "message": "Camera opened for food scanning. Please show me your meal."}

    # --- 6) Phone Calls ---
    def call_someone(self, name: str = None, phone_number: str = None) -> dict:
        """Trigger: 'Call <name/number>,' 'Dial <number>.'"""
        return {
            "status": "confirming",
            "name": name or "Unknown",
            "phone_number": phone_number or "Not provided",
            "message": f"Do you want to make a call to {name or phone_number}?"
        }

    def confirm_call(self, name: str, phone_number: str) -> dict:
        """Trigger: Only after explicit confirmation."""
        return {"status": "dialing", "name": name, "phone_number": phone_number, "message": f"Dialing {name} at {phone_number}."}

    # --- 7) Messaging to Remote Agents ---
    def send_message(self, agent_name: str, query: str) -> dict:
        """Trigger: When specialized remote agent is required."""
        return {"status": "sent", "agent": agent_name, "message": f"Query '{query}' sent to {agent_name}."}

    # --- 8) Scanner & Payments ---
    def open_scanner(self, amount: str = None) -> dict:
        """Trigger: 'scan,' 'scan and pay,' 'scan QR.' Needs amount."""
        if not amount:
            return {"status": "error", "message": "Please provide the amount to proceed."}
        return {"status": "scanner_open", "amount": amount, "message": f"Scanner opened for amount {amount}."}

    # --- 9) Search ---
    def google_search(self, query: str) -> dict:
        """Trigger: explicit or implicit web data needs."""
        return {"status": "success", "query": query, "result": f"Found latest info for '{query}' on Google."}

    def search_nearby_places(self, query: str) -> dict:
        """Triggered for nearby location searches."""
        return {"status": "success", "query": query, "results": ["Place 1", "Place 2"], "message": f"Found nearby {query} for you."}