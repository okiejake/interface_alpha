"""
Audio processing engine for claude-interface.
Captures mic input, detects speech, transcribes with Whisper,
extracts prosodic features, and streams rich JSON to the frontend
via a local WebSocket on ws://localhost:8765.

WebSocket control messages (frontend → engine):
  {"action": "start"}   — enable listening
  {"action": "stop"}    — disable listening

Output messages (engine → frontend):
  {"type": "status",     "status": "loading"|"ready"|"listening"|"processing"|"idle"}
  {"type": "speech_start"}
  {"type": "speech_end"}
  {"type": "transcript", "transcript": "...", "words": [...], "prosody": {...}}
  {"type": "error",      "message": "..."}
"""

import asyncio
import json
import queue
import threading

import numpy as np
import sounddevice as sd
import librosa
import websockets
from faster_whisper import WhisperModel

# ── Audio config ────────────────────────────────────────────────────────────
SAMPLE_RATE = 16_000          # Hz — Whisper native sample rate
CHUNK_SIZE  = 1_024           # samples per callback (~64ms)
SPEECH_THRESHOLD  = 0.015     # RMS level to count as speech
SILENCE_CHUNKS    = 20        # consecutive silent chunks before segment ends (~1.3s)
MIN_SPEECH_CHUNKS = 8         # ignore segments shorter than this (~0.5s)

# ── Model config ─────────────────────────────────────────────────────────────
MODEL_SIZE    = "small"       # tiny / base / small / medium / large-v3
COMPUTE_TYPE  = "int8"        # int8 is fast and accurate enough on CPU


class AudioEngine:
    def __init__(self):
        self.clients: set = set()
        self.listening = False
        self._audio_queue: queue.Queue = queue.Queue()
        self.model: WhisperModel | None = None

    # ── WebSocket plumbing ───────────────────────────────────────────────────

    async def register(self, websocket):
        self.clients.add(websocket)
        print(f"[ws] client connected ({len(self.clients)} total)")
        try:
            async for raw in websocket:
                try:
                    msg = json.loads(raw)
                    await self._handle_command(msg)
                except json.JSONDecodeError:
                    pass
        finally:
            self.clients.discard(websocket)
            print(f"[ws] client disconnected ({len(self.clients)} total)")

    async def _handle_command(self, msg: dict):
        action = msg.get("action")
        if action == "start":
            self.listening = True
            await self.broadcast({"type": "status", "status": "listening"})
            print("[engine] listening started")
        elif action == "stop":
            self.listening = False
            await self.broadcast({"type": "status", "status": "idle"})
            print("[engine] listening stopped")

    async def broadcast(self, data: dict):
        if not self.clients:
            return
        msg = json.dumps(data)
        await asyncio.gather(
            *[c.send(msg) for c in self.clients],
            return_exceptions=True,
        )

    # ── Model loading ────────────────────────────────────────────────────────

    async def load_model(self):
        await self.broadcast({"type": "status", "status": "loading"})
        print(f"[engine] loading Whisper {MODEL_SIZE} …")
        loop = asyncio.get_event_loop()
        self.model = await loop.run_in_executor(
            None,
            lambda: WhisperModel(MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE),
        )
        print("[engine] model ready")
        await self.broadcast({"type": "status", "status": "ready"})

    # ── Audio capture (runs in a background thread) ──────────────────────────

    def _sounddevice_callback(self, indata, frames, time, status):
        if self.listening:
            self._audio_queue.put(indata.copy().flatten())

    # ── Feature extraction ───────────────────────────────────────────────────

    def _extract_prosody(self, audio: np.ndarray) -> dict:
        # Pitch — probabilistic YIN, more robust than plain YIN
        f0, voiced_flag, _ = librosa.pyin(
            audio,
            fmin=librosa.note_to_hz("C2"),   # ~65 Hz  (low male)
            fmax=librosa.note_to_hz("C7"),   # ~2093 Hz (high female/child)
            sr=SAMPLE_RATE,
        )
        f0_voiced = f0[voiced_flag] if voiced_flag is not None and voiced_flag.any() else np.array([0.0])

        # Energy (RMS)
        rms = librosa.feature.rms(y=audio)[0]

        # Timbre — MFCCs give a fingerprint of vocal quality
        mfccs = librosa.feature.mfcc(y=audio, sr=SAMPLE_RATE, n_mfcc=13)
        mfcc_means = mfccs.mean(axis=1).tolist()

        # Spectral centroid — perceived "brightness" of the voice
        centroid = librosa.feature.spectral_centroid(y=audio, sr=SAMPLE_RATE)[0]

        # Zero-crossing rate — correlates with consonant density / voice noisiness
        zcr = librosa.feature.zero_crossing_rate(y=audio)[0]

        return {
            "f0_mean_hz":   float(np.nanmean(f0_voiced)),
            "f0_range_hz":  float(np.nanmax(f0_voiced) - np.nanmin(f0_voiced)),
            # Downsample the contour to 20 points for a readable curve
            "f0_contour":   [
                float(x) for x in
                np.interp(
                    np.linspace(0, len(f0_voiced) - 1, 20),
                    np.arange(len(f0_voiced)),
                    f0_voiced,
                )
            ],
            "energy_mean":  float(np.mean(rms)),
            "energy_max":   float(np.max(rms)),
            "energy_contour": [
                float(x) for x in
                np.interp(np.linspace(0, len(rms) - 1, 20), np.arange(len(rms)), rms)
            ],
            "mfcc_means":         mfcc_means,          # [13 floats] — timbre fingerprint
            "spectral_centroid":  float(np.mean(centroid)),
            "zero_crossing_rate": float(np.mean(zcr)),
            "duration_s":         float(len(audio) / SAMPLE_RATE),
        }

    # ── Inference ────────────────────────────────────────────────────────────

    def _transcribe(self, audio: np.ndarray) -> dict:
        assert self.model is not None
        segments, info = self.model.transcribe(
            audio,
            word_timestamps=True,
            vad_filter=True,
            language=None,          # auto-detect
        )

        words = []
        full_text = ""
        for seg in segments:
            full_text += seg.text
            if seg.words:
                for w in seg.words:
                    words.append({
                        "word":       w.word.strip(),
                        "start":      round(w.start, 3),
                        "end":        round(w.end, 3),
                        "confidence": round(w.probability, 3),
                    })

        duration   = len(audio) / SAMPLE_RATE
        wpm        = (len(words) / duration * 60) if duration > 0 and words else 0
        prosody    = self._extract_prosody(audio)
        prosody["speaking_rate_wpm"] = round(wpm, 1)

        return {
            "type":       "transcript",
            "transcript": full_text.strip(),
            "words":      words,
            "language":   info.language,
            "lang_prob":  round(info.language_probability, 3),
            "prosody":    prosody,
        }

    # ── Main audio loop ──────────────────────────────────────────────────────

    async def run(self):
        await self.load_model()
        loop = asyncio.get_event_loop()

        buffer: list[np.ndarray] = []
        silence_count = 0
        speaking = False

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=CHUNK_SIZE,
            callback=self._sounddevice_callback,
        ):
            print("[engine] microphone open, waiting for 'start' command")

            while True:
                try:
                    chunk = await loop.run_in_executor(
                        None,
                        lambda: self._audio_queue.get(timeout=0.1),
                    )
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue

                rms = float(np.sqrt(np.mean(chunk ** 2)))
                is_speech = rms > SPEECH_THRESHOLD

                if is_speech:
                    if not speaking:
                        speaking = True
                        await self.broadcast({"type": "speech_start"})
                    buffer.append(chunk)
                    silence_count = 0

                elif speaking:
                    buffer.append(chunk)
                    silence_count += 1

                    if silence_count >= SILENCE_CHUNKS:
                        await self.broadcast({"type": "speech_end"})

                        if len(buffer) >= MIN_SPEECH_CHUNKS:
                            audio = np.concatenate(buffer)
                            await self.broadcast({"type": "status", "status": "processing"})

                            try:
                                result = await loop.run_in_executor(
                                    None, self._transcribe, audio
                                )
                                await self.broadcast(result)
                            except Exception as exc:
                                print(f"[engine] transcription error: {exc}")
                                await self.broadcast({"type": "error", "message": str(exc)})

                            await self.broadcast({"type": "status", "status": "listening"})

                        buffer = []
                        silence_count = 0
                        speaking = False


# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    engine = AudioEngine()

    async with websockets.serve(engine.register, "localhost", 8765):
        print("[ws] server listening on ws://localhost:8765")
        await engine.run()


if __name__ == "__main__":
    asyncio.run(main())
