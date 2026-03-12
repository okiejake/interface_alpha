const WS_URL = "ws://localhost:8765";

const orb        = document.getElementById("orb")!;
const statusLabel = document.getElementById("status-label")!;
const micBtn     = document.getElementById("mic-btn")!;
const iconMic    = document.getElementById("icon-mic")!;
const iconMicOff = document.getElementById("icon-mic-off")!;
const feed       = document.getElementById("transcript-feed")!;

let ws: WebSocket | null = null;
let listening = false;

// ── Orb state ──────────────────────────────────────────────────────────────

type OrbState = "idle" | "listening" | "speaking" | "processing";

function setOrbState(state: OrbState) {
  orb.className = state === "idle" ? "" : state;
  statusLabel.textContent = state;
}

// ── WebSocket ──────────────────────────────────────────────────────────────

function connect() {
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    console.log("[ws] connected");
    setOrbState("idle");
  };

  ws.onclose = () => {
    console.log("[ws] disconnected — retrying in 2s");
    setOrbState("idle");
    statusLabel.textContent = "disconnected";
    setTimeout(connect, 2000);
  };

  ws.onerror = (e) => console.error("[ws] error", e);

  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data as string);
    handleMessage(msg);
  };
}

function handleMessage(msg: Record<string, unknown>) {
  switch (msg.type) {
    case "status":
      setOrbState(msg.status as OrbState);
      break;

    case "speech_start":
      setOrbState("speaking");
      break;

    case "speech_end":
      setOrbState("processing");
      break;

    case "transcript":
      addTranscriptCard(msg);
      break;

    case "error":
      console.error("[engine]", msg.message);
      break;
  }
}

// ── Transcript cards ───────────────────────────────────────────────────────

interface TranscriptMsg {
  transcript: string;
  prosody?: {
    f0_mean_hz: number;
    f0_range_hz: number;
    energy_mean: number;
    speaking_rate_wpm: number;
    duration_s: number;
  };
  language?: string;
}

function addTranscriptCard(msg: Record<string, unknown>) {
  const { transcript, prosody, language } = msg as unknown as TranscriptMsg;
  if (!transcript) return;

  const card = document.createElement("div");
  card.className = "transcript-card";

  const text = document.createElement("p");
  text.className = "text";
  text.textContent = transcript;

  const meta = document.createElement("div");
  meta.className = "meta";

  if (prosody) {
    const f0 = prosody.f0_mean_hz > 0 ? `${Math.round(prosody.f0_mean_hz)} Hz` : "—";
    const wpm = prosody.speaking_rate_wpm > 0 ? `${Math.round(prosody.speaking_rate_wpm)} wpm` : "";
    const energy = `energy ${prosody.energy_mean.toFixed(3)}`;
    meta.textContent = [f0, wpm, energy, language].filter(Boolean).join("  ·  ");
  }

  card.appendChild(text);
  if (prosody) card.appendChild(meta);

  feed.prepend(card);
}

// ── Mic toggle ─────────────────────────────────────────────────────────────

function setListening(active: boolean) {
  listening = active;
  micBtn.classList.toggle("active", active);
  iconMic.style.display    = active ? "none"  : "";
  iconMicOff.style.display = active ? ""      : "none";

  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: active ? "start" : "stop" }));
  }
}

micBtn.addEventListener("click", () => setListening(!listening));

// ── Boot ───────────────────────────────────────────────────────────────────

statusLabel.textContent = "connecting…";
connect();
