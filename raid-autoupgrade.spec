# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build definition for the one-file Windows exe (see ADR 0003).

Onefile, windowed (no console), self-elevating via a requireAdministrator
manifest. The built React frontend is bundled as data and resolved at runtime
through ``utils.resources.resource_path`` (sys._MEIPASS-aware).

Build locally with:  uv run pyinstaller raid-autoupgrade.spec
"""

import tomllib

from PyInstaller.utils.hooks import collect_all, collect_submodules
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

# Single source of truth for the version: pyproject.toml (the CI version guard
# already enforces tag == this value). An unsigned exe with no version metadata
# looks more suspicious to antivirus heuristics, so embed a proper resource.
with open("pyproject.toml", "rb") as _f:
    _VERSION = tomllib.load(_f)["project"]["version"]
_FILEVERS = (tuple(int(p) for p in _VERSION.split(".")) + (0, 0, 0, 0))[:4]

version_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=_FILEVERS,
        prodvers=_FILEVERS,
        mask=0x3F,
        flags=0x0,
        OS=0x40004,  # VOS_NT_WINDOWS32
        fileType=0x1,  # VFT_APP
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040904B0",  # US English, Unicode codepage
                    [
                        StringStruct("CompanyName", "Raijin"),
                        StringStruct(
                            "FileDescription",
                            "Raid Autoupgrade - upgrade automation for "
                            "Raid: Shadow Legends",
                        ),
                        StringStruct("FileVersion", _VERSION),
                        StringStruct("InternalName", "RaidAutoupgrade"),
                        StringStruct("OriginalFilename", "RaidAutoupgrade.exe"),
                        StringStruct("ProductName", "Raid Autoupgrade"),
                        StringStruct("ProductVersion", _VERSION),
                        StringStruct(
                            "LegalCopyright", "Personal use only. See LICENSE."
                        ),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
    ],
)

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
    upx=False,  # UPX-packed binaries trip antivirus heuristics more often
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    version=version_info,
)
