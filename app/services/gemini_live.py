import asyncio
import json
import base64
import websockets
from app.core.config import settings
from app.core.logging import gemini_logger

class GeminiLiveClient:
    """
    Manages a real-time, bi-directional WebSocket connection with Gemini Live API (Multimodal Live API).
    Sends raw PCM audio / text triggers and receives model audio responses with tool calls.
    """

    def __init__(self, system_instruction: str):
        self.api_key = settings.GEMINI_API_KEY
        # Gemini 2.0 Flash Realtime WebSockets Endpoint
        self.uri = (
            f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent"
            f"?key={self.api_key}"
        )
        self.system_instruction = system_instruction
        self.websocket = None
        self.session_id = None

    async def connect(self):
        """Establishes WebSocket connection to Gemini Live and sends setup frame."""
        gemini_logger.info("Connecting to Gemini Live Multimodal WebSocket API...")
        self.websocket = await websockets.connect(self.uri)

        # Setup configuration payload defining tools, model voice, and system instructions
        setup_payload = {
            "setup": {
                "model": "models/gemini-2.0-flash-exp",
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {
                                "voiceName": "Kore"  # Warm, professional Hindi voice candidate
                            }
                        }
                    }
                },
                "systemInstruction": {
                    "parts": [
                        {"text": self.system_instruction}
                    ]
                },
                "tools": [
                    {
                        "functionDeclarations": [
                            {
                                "name": "check_availability",
                                "description": "Checks available doctor appointment slots for a specific date (Format: YYYY-MM-DD).",
                                "parameters": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "doctor_id": {"type": "STRING", "description": "Doctor ID (doc_ortho, doc_cardio, doc_eye)"},
                                        "target_date": {"type": "STRING", "description": "ISO date YYYY-MM-DD"}
                                    },
                                    "required": ["doctor_id", "target_date"]
                                }
                            },
                            {
                                "name": "book_appointment",
                                "description": "Books a doctor appointment for a patient after confirmation.",
                                "parameters": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "patient_name": {"type": "STRING", "description": "Full name of patient"},
                                        "doctor_id": {"type": "STRING", "description": "Doctor ID (doc_ortho, doc_cardio, doc_eye)"},
                                        "appointment_datetime": {"type": "STRING", "description": "ISO Datetime YYYY-MM-DDTHH:MM:SS"},
                                        "reason": {"type": "STRING", "description": "Medical issue or reason for visit"}
                                    },
                                    "required": ["patient_name", "doctor_id", "appointment_datetime"]
                                }
                            },
                            {
                                "name": "get_active_bookings",
                                "description": "Fetches active appointments booked for the patient's phone number.",
                                "parameters": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "phone": {"type": "STRING", "description": "Patient phone number"}
                                    }
                                }
                            },
                            {
                                "name": "save_patient_intake",
                                "description": "Saves medical intake details collected from outbound call.",
                                "parameters": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "appointment_id": {"type": "STRING", "description": "Appointment ID"},
                                        "has_visited_before": {"type": "BOOLEAN", "description": "Has visited before"},
                                        "previous_doctor": {"type": "STRING", "description": "Previous doctor name"},
                                        "has_reports": {"type": "BOOLEAN", "description": "Has test reports"},
                                        "report_details": {"type": "STRING", "description": "Report details"},
                                        "current_medicines": {"type": "STRING", "description": "Current medicines"},
                                        "additional_notes": {"type": "STRING", "description": "Additional notes"}
                                    },
                                    "required": ["appointment_id"]
                                }
                            }
                        ]
                    }
                ]
            }
        }

        await self.websocket.send(json.dumps(setup_payload))
        gemini_logger.info("Sent setup frame to Gemini Live WebSocket.")

    async def send_audio_chunk(self, pcm_data):
        """Sends raw 16kHz 16-bit PCM audio chunk to Gemini WebSocket."""
        if not self.websocket:
            return

        if isinstance(pcm_data, str):
            audio_b64 = pcm_data
        else:
            audio_b64 = base64.b64encode(pcm_data).decode("utf-8")

        media_payload = {
            "realtimeInput": {
                "mediaChunks": [
                    {
                        "mimeType": "audio/pcm;rate=16000",
                        "data": audio_b64
                    }
                ]
            }
        }
        await self.websocket.send(json.dumps(media_payload))

    async def send_text_trigger(self, prompt_text: str):
        """Sends text prompt trigger to Gemini Live to initiate or guide conversation."""
        if not self.websocket:
            return

        text_payload = {
            "clientContent": {
                "turns": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt_text}]
                    }
                ],
                "turnComplete": True
            }
        }
        await self.websocket.send(json.dumps(text_payload))
        gemini_logger.info(f"Sent text trigger prompt to Gemini Live: {prompt_text[:60]}...")

    async def send_tool_response(self, call_id: str, function_name: str, response_dict: dict):
        """Sends tool execution result back to Gemini WebSocket."""
        if not self.websocket:
            return

        tool_response_payload = {
            "toolResponse": {
                "functionResponses": [
                    {
                        "response": response_dict,
                        "id": call_id
                    }
                ]
            }
        }
        await self.websocket.send(json.dumps(tool_response_payload))
        gemini_logger.info(f"Sent tool execution response for {function_name} to Gemini Live.")

    async def receive_events(self):
        """Async generator yielding model events from Gemini WebSocket."""
        if not self.websocket:
            return

        async for message in self.websocket:
            try:
                data = json.loads(message)
                server_content = data.get("serverContent")
                if server_content:
                    model_turn = server_content.get("modelTurn")
                    if model_turn:
                        for part in model_turn.get("parts", []):
                            # Audio response chunk
                            if "inlineData" in part:
                                inline_data = part["inlineData"]
                                if inline_data.get("mimeType", "").startswith("audio/pcm"):
                                    pcm_b64 = inline_data.get("data")
                                    pcm_bytes = base64.b64decode(pcm_b64)
                                    yield {"type": "audio", "data": pcm_bytes}

                            # Text turn / model message
                            elif "text" in part:
                                yield {"type": "text", "text": part["text"]}

                    # Check for turn completion
                    if server_content.get("turnComplete"):
                        yield {"type": "turn_complete"}

                    # Check for user interruption
                    if server_content.get("interrupted"):
                        yield {"type": "interrupted"}

                # Tool Calls from model
                tool_call = data.get("toolCall")
                if tool_call:
                    for function_call in tool_call.get("functionCalls", []):
                        yield {
                            "type": "tool_call",
                            "call_id": function_call.get("id"),
                            "name": function_call.get("name"),
                            "args": function_call.get("args", {})
                        }

            except Exception as e:
                gemini_logger.error(f"Error parsing Gemini Live WebSocket message: {str(e)}")

    async def receive_stream(self):
        """Alias method for receive_events generator."""
        async for event in self.receive_events():
            yield event

    async def close(self):
        """Closes the Gemini WebSocket connection gracefully."""
        if self.websocket:
            await self.websocket.close()
            gemini_logger.info("Closed Gemini Live WebSocket connection.")
