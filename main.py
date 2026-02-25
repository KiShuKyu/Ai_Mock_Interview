import asyncio
import os
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from google import genai
import pyaudio

load_dotenv()

# ── PyAudio config ────────────────────────────────────────────────────────────
FORMAT          = pyaudio.paInt16
CHANNELS        = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE      = 1024

# ── Gemini config ─────────────────────────────────────────────────────────────
MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"


def build_system_prompt(role: str, company: str, focus: str, difficulty: str) -> str:
    return f"""You are Alex, a professional technical interviewer conducting a mock interview.

Session details:
- Role: {role}
- Company type: {company}
- Interview focus: {focus}
- Difficulty: {difficulty}

Instructions:
- Start by greeting the candidate and asking them to introduce themselves.
- Ask one question at a time and wait for a full answer before continuing.
- Ask 6–8 questions total, increasing in depth as the interview progresses.
- Give brief, natural acknowledgements between questions (e.g. "Got it", "Interesting").
- At the end, thank the candidate and tell them the session is complete.
- Be professional but warm. Do NOT give scores or feedback during the interview.
"""


# ── Active sessions ───────────────────────────────────────────────────────────
active_sessions: dict[str, "InterviewSession"] = {}


class InterviewSession:
    def __init__(self, session_id: str, config: dict, ws: WebSocket):
        self.session_id   = session_id
        self.config       = config
        self.ws           = ws
        self.pya          = pyaudio.PyAudio()
        self.audio_out_q  = asyncio.Queue()
        self.audio_mic_q  = asyncio.Queue(maxsize=5)
        self.mic_stream   = None
        self.spk_stream   = None
        self.running      = False
        self.tasks: list[asyncio.Task] = []

    # ── send status/transcript events to the browser ──────────────────────────
    async def send_event(self, event_type: str, **kwargs):
        try:
            await self.ws.send_text(json.dumps({"type": event_type, **kwargs}))
        except Exception:
            pass

    # ── mic → queue ───────────────────────────────────────────────────────────
    async def listen_audio(self):
        mic_info = self.pya.get_default_input_device_info()
        self.mic_stream = await asyncio.to_thread(
            self.pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        while self.running:
            data = await asyncio.to_thread(
                self.mic_stream.read, CHUNK_SIZE, exception_on_overflow=False
            )
            await self.audio_mic_q.put({"data": data, "mime_type": "audio/pcm"})

    # ── queue → Gemini ─────────────────────────────────────────────────────────
    async def send_realtime(self, live_session):
        while self.running:
            msg = await self.audio_mic_q.get()
            await live_session.send_realtime_input(audio=msg)

    # ── Gemini → speaker queue ─────────────────────────────────────────────────
    async def receive_audio(self, live_session):
        while self.running:
            await self.send_event("ai_state", state="speaking")
            turn = live_session.receive()
            async for response in turn:
                if response.server_content and response.server_content.model_turn:
                    for part in response.server_content.model_turn.parts:
                        if part.inline_data and isinstance(part.inline_data.data, bytes):
                            self.audio_out_q.put_nowait(part.inline_data.data)

                # Text transcript (if available)
                if response.server_content and response.server_content.output_transcription:
                    text = response.server_content.output_transcription.text
                    if text:
                        await self.send_event("transcript", speaker="Alex", text=text)

            # Turn finished → flush speaker queue (handles interruptions)
            while not self.audio_out_q.empty():
                self.audio_out_q.get_nowait()
            await self.send_event("ai_state", state="listening")

    # ── speaker queue → audio out ─────────────────────────────────────────────
    async def play_audio(self):
        self.spk_stream = await asyncio.to_thread(
            self.pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        while self.running:
            data = await self.audio_out_q.get()
            await asyncio.to_thread(self.spk_stream.write, data)

    # ── main session loop ─────────────────────────────────────────────────────
    async def run(self):
        self.running = True
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        gemini_config = {
            "response_modalities": ["AUDIO"],
            "system_instruction": build_system_prompt(
                self.config.get("role", "Software Engineer"),
                self.config.get("company", "Tech Company"),
                self.config.get("focus", "Behavioral"),
                self.config.get("difficulty", "Mid Level"),
            ),
        }
        try:
            async with client.aio.live.connect(model=MODEL, config=gemini_config) as live_session:
                await self.send_event("status", message="connected")
                async with asyncio.TaskGroup() as tg:
                    self.tasks = [
                        tg.create_task(self.listen_audio()),
                        tg.create_task(self.send_realtime(live_session)),
                        tg.create_task(self.receive_audio(live_session)),
                        tg.create_task(self.play_audio()),
                    ]
        except Exception as e:
            await self.send_event("error", message=str(e))
        finally:
            self.cleanup()

    def stop(self):
        self.running = False
        for t in self.tasks:
            t.cancel()

    def cleanup(self):
        if self.mic_stream:
            try: self.mic_stream.close()
            except: pass
        if self.spk_stream:
            try: self.spk_stream.close()
            except: pass
        try: self.pya.terminate()
        except: pass


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("index.html", encoding="utf-8") as f:
        return f.read()


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = None
    try:
        # First message must be the interview config
        raw = await websocket.receive_text()
        config = json.loads(raw)

        session = InterviewSession(session_id, config, websocket)
        active_sessions[session_id] = session

        await session.run()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except:
            pass
    finally:
        if session:
            session.stop()
            active_sessions.pop(session_id, None)