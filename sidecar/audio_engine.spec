# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for audio_engine sidecar binary

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['audio_engine.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'faster_whisper',
        'ctranslate2',
        'huggingface_hub',
        'tokenizers',
        'sounddevice',
        'librosa',
        'scipy.signal',
        'scipy.fft',
        'numpy',
        'websockets',
        'websockets.legacy',
        'websockets.legacy.server',
        '_sounddevice_data',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'PIL',
        'IPython',
        'jupyter',
        'pytest',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='audio-engine',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    target_arch='arm64',
    info_plist={
        'NSMicrophoneUsageDescription': '_α uses the microphone for real-time speech transcription and audio analysis.',
        'CFBundleName': 'audio-engine',
        'CFBundleIdentifier': 'com.jacob.claude-interface.audio-engine',
    },
)
