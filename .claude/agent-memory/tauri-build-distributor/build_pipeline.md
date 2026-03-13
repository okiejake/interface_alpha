---
name: build_pipeline
description: Verified production build pipeline for claude-interface — commands, artifact paths, sizes, warnings, and gotchas
type: project
---

## Verified Production Build (2026-03-12)

### Build command
```
source ~/.cargo/env && npm run tauri build
```
`tauri build` triggers `beforeBuildCommand: npm run build:all`, which runs:
1. `bash scripts/build-sidecar.sh` — PyInstaller builds `sidecar/audio_engine.py` → `sidecar/dist/audio-engine`, then copies to `src-tauri/binaries/audio-engine-aarch64-apple-darwin`
2. `tsc && vite build` — TypeScript compile + Vite frontend bundle → `dist/`
3. Cargo release build → Tauri bundles `.app` and `.dmg`

### Artifact locations
- `.app`: `src-tauri/target/release/bundle/macos/claude-interface.app` (135 MB)
- `.dmg`: `src-tauri/target/release/bundle/dmg/claude-interface_0.1.0_aarch64.dmg` (128 MB)
- Sidecar binary: `src-tauri/binaries/audio-engine-aarch64-apple-darwin` (124 MB)

### Toolchain versions that worked
- PyInstaller 6.19.0, Python 3.13.1
- Rust 1.94.0 / Cargo 1.94.0
- Vite 6.4.1
- Tauri CLI 2.x, tauri 2.10.3

### Known warnings (non-fatal)
- Several scipy `.so` files have SDK version `(0, 0, 0)` — PyInstaller warns these "will likely cause issues with code-signing and hardened runtime." Build succeeds but ad-hoc signed only (no Apple Developer ID). Will matter for notarized distribution.
- `ole32` / `shell32` ctypes warnings — macOS-irrelevant Windows libs, safe to ignore.
- `pycparser.lextab` / `pycparser.yacctab` hidden import not found — non-fatal.
- `scipy.special._cdflib` hidden import not found — non-fatal.

### Tauri externalBin config
`tauri.conf.json` → `bundle.externalBin: ["binaries/audio-engine"]`
Tauri appends the target triple; binary must be at `src-tauri/binaries/audio-engine-aarch64-apple-darwin`.

### Code signing status
No Apple Developer ID configured. App is ad-hoc signed. For distribution outside this machine, notarization via `xcrun notarytool` will be required, and the scipy SDK-version warnings will need resolution (recompile scipy against matching SDK or use `codesign --deep --force`).

**Why:** First production build run; capturing baseline for future sessions.
**How to apply:** Use these paths and warnings as the baseline when diagnosing future build failures or preparing for distribution.
