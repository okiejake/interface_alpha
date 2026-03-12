# interface_alpha

> A human/AI collaboration interface that gives Claude ears — and eventually eyes.

Built on the belief that the bottleneck in human/AI collaboration isn't intelligence, it's bandwidth. Text input is slow. This project explores what becomes possible when you can speak naturally, and the AI understands not just *what* you said but *how* you said it.

---

## What it does

- **Speaks to Claude** — capture your voice via mic, transcribe locally with Whisper
- **Understands prosody** — extracts pitch (F0), energy, speaking rate, timbre, and more from every utterance
- **Runs locally** — no audio or transcripts leave your machine; all processing is on-device
- **Ambient presence** — a pulsing orb UI that reflects the engine's state in real time

This is early. The roadmap includes Claude responding via voice, camera input for visual context, speaker recognition, and more.

---

## Architecture

```
Microphone
    ↓
Python sidecar (sidecar/audio_engine.py)
    ├── sounddevice       — mic capture
    ├── faster-whisper    — local STT, word-level timestamps
    ├── librosa           — pitch, energy, MFCCs, spectral features
    └── WebSocket :8765   — streams JSON events to frontend
    ↓
Tauri + TypeScript frontend
    ├── Orb UI            — animated state indicator
    ├── Mic toggle        — start/stop listening
    └── Transcript feed   — live cards with text + prosody metadata
```

All audio processing is local. The only network call is to the Claude API when a response is requested (not yet implemented in this alpha).

---

## Prerequisites

| Dependency | Version | Notes |
|---|---|---|
| Node.js | 20+ | |
| Rust | 1.70+ | Install via [rustup](https://rustup.rs) |
| Python | 3.10+ | 3.13 recommended |
| Xcode CLI tools | any | macOS only — `xcode-select --install` |

---

## Getting started

### 1. Install frontend dependencies
```bash
npm install
```

### 2. Set up the Python sidecar
```bash
python3 -m venv sidecar/.venv
sidecar/.venv/bin/pip install -r sidecar/requirements.txt
```

The first run will download the Whisper `small` model (~500MB) to `~/.cache/huggingface/hub/`. Subsequent starts are instant.

### 3. Start the audio engine
```bash
PYTHONUNBUFFERED=1 sidecar/.venv/bin/python -u sidecar/audio_engine.py
```

You should see:
```
[ws] server listening on ws://localhost:8765
[engine] loading Whisper small …
[engine] model ready
[engine] microphone open, waiting for 'start' command
```

### 4. Start the app
```bash
npm run tauri dev
```

Click the mic button in the window, speak, and watch the transcript cards appear.

---

## Prosody data

Every transcript includes rich audio metadata:

```json
{
  "transcript": "I want to build something incredible",
  "words": [
    { "word": "I", "start": 0.0, "end": 0.12, "confidence": 0.99 }
  ],
  "prosody": {
    "f0_mean_hz": 142.3,
    "f0_range_hz": 68.1,
    "f0_contour": [...],
    "energy_mean": 0.072,
    "speaking_rate_wpm": 148.0,
    "mfcc_means": [...],
    "spectral_centroid": 1840.2,
    "duration_s": 3.2
  }
}
```

---

## Roadmap

- [x] Local STT with word-level timestamps (faster-whisper)
- [x] Prosody extraction (F0, energy, MFCCs, speaking rate)
- [x] Orb UI with animated state machine
- [x] Mic toggle → WebSocket → transcript cards
- [ ] Claude API integration — transcript + prosody → response
- [ ] TTS output — Claude speaks back, orb pulses with amplitude
- [ ] Camera feed — snapshot per query for Claude vision context
- [ ] Speaker diarization — identify who is speaking
- [ ] Speaker learning — build voice embeddings over time
- [ ] Auto-launch sidecar from Tauri on app start

---

## Contributing

This project is in early alpha and moving fast. All contributions welcome.

**Good first issues:**
- Improve VAD sensitivity / silence detection tuning
- Add jitter/shimmer extraction via [parselmouth](https://github.com/YannickJadoul/Parselmouth)
- Build a settings panel (model size, mic device selection)
- Windows / Linux compatibility testing

**Before submitting a PR:**
1. Branch from `dev`, not `main`
2. Keep PRs focused — one feature or fix per PR
3. Test that the sidecar starts cleanly and transcription works end to end

```bash
git checkout dev
git checkout -b feat/your-feature
# ... make changes ...
git push origin feat/your-feature
# open PR → dev
```

**Branch strategy:**
```
main          stable releases
dev           integration — all features merge here first
feat/*        active feature work
```

---

## Stack

| Layer | Technology |
|---|---|
| Desktop shell | [Tauri 2](https://tauri.app) |
| Frontend | Vanilla TypeScript + Vite |
| Audio capture | [sounddevice](https://python-sounddevice.readthedocs.io) |
| Speech-to-text | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) |
| Audio analysis | [librosa](https://librosa.org) |
| IPC | WebSocket (localhost:8765) |

---

## License

MIT
