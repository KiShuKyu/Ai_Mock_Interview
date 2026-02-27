# AI Mock Interview

A browser-based mock interview tool powered by the **Gemini 2.5 Flash Live API**. Configure your role, company type, and difficulty — then just talk. The AI interviews you in real time, voice to voice, no typing required.

---

## How It Works

The backend is a FastAPI server that owns the entire audio pipeline. On session start it opens your microphone via PyAudio, streams raw PCM audio to Gemini's Live API at 16 kHz, and plays the AI's response back through your speakers at 24 kHz — all in real time.

The browser connects over a WebSocket and receives transcript and state events (`speaking`, `listening`) to keep the UI in sync. Audio never touches the browser; it flows entirely through your system mic and speakers via the Python backend.

---

## Requirements

- **Python 3.11** — required. PyAudio wheels are version-specific on Windows; 3.11 is the tested target.
- A [Google AI Studio](https://aistudio.google.com) API key with Gemini Live access.

---

## Setup

### 1. Install PyAudio

PyAudio is the only tricky dependency. A plain `pip install pyaudio` will likely fail on Windows with a C++ build error. Use the prebuilt wheel instead:

```bash
pip install pipwin
pipwin install pyaudio
```

If `pipwin` doesn't work for your setup, download the correct `.whl` directly from [Christoph Gohlke's unofficial binaries](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio). For Python 3.11 64-bit, you want:

```
PyAudio-0.2.14-cp311-cp311-win_amd64.whl
```

Install it with:

```bash
pip install PyAudio-0.2.14-cp311-cp311-win_amd64.whl
```

### 2. Install remaining dependencies

```bash
pip install -r requirements.txt
```

### 3. Add your API key

Create a `.env` file in the project root:

```
GOOGLE_API_KEY=your_key_here
```

### 4. Start the server

```bash
uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Project Structure

```
testing/
├── main.py          ← FastAPI backend — WebSocket, Gemini Live session, audio loop
├── index.html       ← Full frontend (setup → live interview → results)
├── app.js           ← Frontend JS
├── style.css        ← Frontend styles
├── .env             ← Your API key (never commit this)
├── requirements.txt
└── README.md
```

---

## Troubleshooting

**`UnicodeDecodeError: 'charmap' codec`**
Python is reading `index.html` with the wrong encoding. Make sure the file open call in `main.py` includes `encoding="utf-8"`. It should already be there — don't remove it if you ever refactor that line.

**Transcript not showing in browser**
The live transcript depends on `output_transcription` from the model. If messages aren't appearing, add `"TEXT"` to the `response_modalities` list in `main.py`. Audio through your speakers will work either way.

**Audio sounds distorted or wrong pitch**
The Gemini Live API is strict about sample rates. Mic input must be **16 kHz**, speaker output must be **24 kHz**. Don't change these values.

**Multiple tabs conflict**
Each session opens your physical mic and speakers. Running two sessions at the same time from different browser tabs will cause audio device conflicts — one session at a time only.

---

## Notes

- `.env` is gitignored — never commit your API key.
- The frontend is intentionally self-contained. Setup form, live interview view, and results summary are all in `index.html` with no external dependencies.