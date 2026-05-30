# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build definition for the one-file Windows exe (see ADR 0003).

Onefile, windowed (no console), self-elevating via a requireAdministrator
manifest. The built React frontend is bundled as data and resolved at runtime
through ``utils.resources.resource_path`` (sys._MEIPASS-aware).

Build locally with:  uv run pyinstaller raid-autoupgrade.spec
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

# The built frontend (gitignored; produced by `npm run build` in CI) is served
# as static files by FastAPI, so it must travel inside the bundle.
datas = [("frontend/dist", "frontend/dist")]
binaries = []
hiddenimports = []

# Native / dynamically-imported packages PyInstaller does not trace cleanly.
# collect_all pulls their submodules, data files, and bundled binaries.
for package in ("cv2", "webview", "wmi", "pywinauto"):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

# uvicorn[standard] loads its loop/protocol/lifespan backends lazily by string,
# so the auto-selectors and their websocket/http extras must be forced in.
hiddenimports += collect_submodules("uvicorn")
hiddenimports += [
    "uvicorn.lifespan.on",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "websockets",
    "httptools",
]

a = Analysis(
    ["packaging/entry.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="RaidAutoupgrade",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
)
