#!/usr/bin/env bash
# Build the audio-engine sidecar binary with PyInstaller
# and place it where Tauri expects it.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SIDECAR_DIR="$REPO_ROOT/sidecar"
TARGET_DIR="$REPO_ROOT/src-tauri/binaries"

# Detect target triple
TARGET_TRIPLE="$(rustc -vV | sed -n 's/host: //p')"
echo "→ Building sidecar for $TARGET_TRIPLE"

# Build with PyInstaller
cd "$SIDECAR_DIR"
"$SIDECAR_DIR/.venv/bin/python" -m PyInstaller \
    --distpath "$SIDECAR_DIR/dist" \
    --workpath "$SIDECAR_DIR/build" \
    --clean \
    --noconfirm \
    audio_engine.spec

# Place binary where Tauri expects it
mkdir -p "$TARGET_DIR"
cp "$SIDECAR_DIR/dist/audio-engine" "$TARGET_DIR/audio-engine-$TARGET_TRIPLE"
echo "→ Sidecar binary placed at $TARGET_DIR/audio-engine-$TARGET_TRIPLE"
