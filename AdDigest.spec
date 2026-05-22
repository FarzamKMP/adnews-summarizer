# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# Collect all data files that must be bundled
added_files = [
    ("web",         "web"),
    ("data",        "data"),
    ("modules",     "modules"),
]

from PyInstaller.utils.hooks import collect_all, collect_submodules

chroma_datas, chroma_binaries, chroma_hidden = collect_all("chromadb")
added_files += chroma_datas

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=chroma_binaries,
    datas=added_files,
    hiddenimports=chroma_hidden + [
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.main",
        "fastapi",
        "starlette",
        "sqlalchemy",
        "sqlalchemy.dialects.sqlite",
        "pydantic",
        "apscheduler",
        "apscheduler.schedulers.background",
        "apscheduler.triggers.interval",
        "feedparser",
        "newspaper",
        "bs4",
        "lxml",
        "lxml.etree",
        "lxml.html",
        "chromadb",
        "chromadb.db.impl",
        "chromadb.db.impl.sqlite",
        "chromadb.telemetry",
        "chromadb.telemetry.product",
        "chromadb.telemetry.product.posthog",
        "chromadb.segment",
        "chromadb.segment.impl",
        "chromadb.segment.impl.manager",
        "chromadb.segment.impl.manager.local",
        "chromadb.segment.impl.metadata",
        "chromadb.segment.impl.metadata.sqlite",
        "chromadb.segment.impl.vector",
        "chromadb.segment.impl.vector.local_persistent_hnsw",
        "chromadb.segment.impl.vector.local_hnsw",
        "chromadb.execution",
        "chromadb.execution.executor",
        "chromadb.execution.executor.local",
        "chromadb.migrations",
        "chromadb.migrations.embeddings_queue",
        "posthog",
        "onnxruntime",
        "google.genai",
        "google.auth",
        "google.auth.transport",
        "dotenv",
        "PIL",
        "pystray",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AdDigest",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # no terminal window
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="AdDigest",
)

# Mac .app bundle
app = BUNDLE(
    coll,
    name="AdDigest.app",
    icon=None,
    bundle_identifier="com.jvmhavel.addigest",
    info_plist={
        "NSHighResolutionCapable": True,
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleName": "AdDigest",
        "NSAppleEventsUsageDescription": "AdDigest needs access to open your browser.",
    },
)
