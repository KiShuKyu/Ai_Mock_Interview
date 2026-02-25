# AI Mock Interview

A browser-based mock interview tool powered by the Gemini 2.5 Flash Live API. It runs a real-time voice-to-voice conversation between you and an AI interviewer — no typing, no clicking next, just talking. You configure the role, company type, and difficulty, hit start, and have a live interview through your browser.

## How it works

The backend is a FastAPI server that manages the full audio pipeline. When you start a session, it opens your microphone via PyAudio, streams raw PCM audio to Gemini's Live API at 16kHz, and plays the AI's response back through your speakers at 24kHz — all in real time. The browser connects over a WebSocket and receives transcript and state events (speaking, listening) to keep the UI in sync. Audio never touches the browser; it all goes through your system mic and speakers via the Python backend.

## Python Version

This project is built and tested on **Python 3.11**. This matters because of PyAudio — see the installation note below before you try to `pip install` anything.

## Setup

**1. Install PyAudio (read this first)**

PyAudio is the trickiest dependency on Windows. If you just run `pip install pyaudio` you'll likely hit a build error asking for *Microsoft C++ Build Tools*. Skip that headache and install the prebuilt wheel instead:

```bash
pip install pipwin
pipwin install pyaudio
```

If `pipwin` doesn't work for your Python version, grab the correct `.whl` file directly from [Christoph Gohlke's unofficial binaries](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio). Match the filename to your Python version and architecture — for Python 3.11 64-bit you want something like `PyAudio‑0.2.14‑cp311‑cp311‑win_amd64.whl` — then install it with:

```bash
pip install PyAudio‑0.2.14‑cp311‑cp311‑win_amd64.whl
```

**2. Install the rest of the dependencies**

```bash
pip install -r requirements.txt
```

**3. Set your API key**

Create a `.env` file in the project folder:

```
GOOGLE_API_KEY=your_key_here
```

Get a key from [Google AI Studio](https://aistudio.google.com).

**4. Run the server**

```bash
uvicorn main:app --reload
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

## The Files

- `main.py` — FastAPI backend. Handles the WebSocket connection, spins up the Gemini Live session, and manages the mic → Gemini → speaker audio loop. Also serves `index.html`.
- `index.html` — The entire frontend in one file. Three screens: setup form, live interview view with transcript, and a results summary.
- `requirements.txt` — All Python dependencies.
- `.env` — Your API key (create this yourself, don't commit it).

## A few things to watch out for

**Windows encoding error** — If you see a `UnicodeDecodeError: 'charmap' codec` when the server starts, it means Python is reading `index.html` with the wrong encoding. The fix is already in `main.py` (`open("index.html", encoding="utf-8")`), but if you ever edit the file reading logic, keep that `encoding` argument.

**Transcript not showing in browser** — The live transcript relies on `output_transcription` being available from the model. If messages aren't appearing, add `"TEXT"` to the `response_modalities` list in `main.py`. Audio will still play through your speakers either way.

**Sample rates** — The Gemini Live API is strict about this. Mic input must be 16kHz, speaker output must be 24kHz. Changing these will make the AI sound distorted or at the wrong pitch.

**One session at a time** — The current setup opens your physical mic and speakers per session. Running multiple sessions simultaneously from different browser tabs will conflict at the audio device level.
