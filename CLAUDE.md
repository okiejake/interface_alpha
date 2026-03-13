# claude-interface — Project Context

## What this is
A Tauri desktop app that gives Claude eyes and ears — local mic capture with deep audio
analysis, real-time transcription, and eventually camera + TTS response. The goal is the
most efficient possible human/AI collaboration interface: ambient, always-present, low-friction.

## Architecture

```
Microphone
    ↓
sidecar/audio_engine.py   (Python — owns all audio)
    ├── sounddevice        direct mic capture
    ├── faster-whisper     local STT (small model, int8, Apple Silicon CPU)
    ├── librosa            pitch (F0), energy, MFCCs, speaking rate
    └── WebSocket :8765    streams JSON to frontend
    ↓
src-tauri/src/lib.rs       (Rust — app lifecycle)
    ├── tauri-plugin-shell spawns sidecar binary on app start
    ├── Logs sidecar stdout/stderr
    └── Kills sidecar on app exit
    ↓
src/main.ts               (TypeScript frontend)
    ├── WebSocket client   receives transcript + prosody events
    ├── Orb UI             animated violet orb reflects engine state
    └── Transcript feed    cards with text + prosody metadata
```

## Running locally

**Build the sidecar binary** (first time, or after changing `audio_engine.py`):
```bash
npm run build:sidecar
```

**Start Tauri dev** (sidecar auto-launches):
```bash
source ~/.cargo/env
npm run tauri dev
```

Then click the mic button in the app to start listening.

**For production build:**
```bash
source ~/.cargo/env
npm run tauri build
```
This runs `build:all` (PyInstaller + Vite) then packages the app with the sidecar bundled.

## Environment
- macOS arm64 (Apple Silicon), Darwin 25.3.0
- Python 3.13.1 — venv at `sidecar/.venv/`
- Node v20.12.1
- Rust 1.94.0 — at `~/.cargo/bin/` (not on PATH by default — `source ~/.cargo/env`)
- Whisper model cached at `~/.cache/huggingface/hub/` (downloaded on first run, ~500MB)

## Branch strategy
```
main          stable releases only
dev           integration — features merge here before main
feat/*        active feature work → PR to dev
```
Currently active: `feat/audio-engine`

## WebSocket protocol (port 8765)

**Frontend → sidecar:**
```json
{ "action": "start" }   // enable mic listening
{ "action": "stop"  }   // disable mic listening
```

**Sidecar → frontend:**
```json
{ "type": "status",      "status": "loading|ready|listening|processing|idle" }
{ "type": "speech_start" }
{ "type": "speech_end"   }
{ "type": "transcript",  "transcript": "...", "words": [...], "prosody": { ... } }
{ "type": "error",       "message": "..." }
```

**Prosody shape:**
```json
{
  "f0_mean_hz": 142.3,
  "f0_range_hz": 68.1,
  "f0_contour": [20 floats],
  "energy_mean": 0.072,
  "energy_max": 0.21,
  "energy_contour": [20 floats],
  "mfcc_means": [13 floats],
  "spectral_centroid": 1840.2,
  "zero_crossing_rate": 0.043,
  "duration_s": 3.2,
  "speaking_rate_wpm": 148.0
}
```

## Design principles
- **100% local audio processing** — no audio or transcripts leave the machine
- **Ambient presence** — the orb is always visible, mic is opt-in via toggle
- **Rich context over raw text** — every transcript carries prosody metadata so Claude
  understands *how* something was said, not just what
- **No framework bloat** — vanilla TypeScript frontend, no React/Vue

## What's done
- [x] Tauri 2 scaffold + Python sidecar
- [x] Local Whisper STT with word-level timestamps
- [x] Prosody extraction (F0, energy, MFCCs, spectral centroid, ZCR, WPM)
- [x] Animated orb UI (idle / listening / speaking / processing states)
- [x] Mic toggle → WebSocket → transcript cards with metadata

## What's next
- [ ] Wire Claude API: transcript → Claude (with prosody context) → response
- [ ] TTS output: Claude's response spoken back, orb pulses with amplitude
- [ ] Speaker diarization via pyannote.audio (identify speakers by voice)
- [ ] Camera feed: snapshot per query sent to Claude for vision context
- [x] Auto-launch sidecar from Tauri (Rust spawns PyInstaller binary on app start)
- [ ] Speaker learning: build voice embeddings over time to recognize people
