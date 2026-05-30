"""pywebview + FastAPI launcher for the Raid Autoupgrade GUI.

Starts FastAPI in-process on 127.0.0.1 and opens a native pywebview window.
Dev mode (RAID_AUTOUPGRADE_DEV=1): window points at the Vite dev server (HMR).
Prod mode: FastAPI serves the built frontend/dist/ as static files.
"""

import os
import threading
import time
from pathlib import Path

import diskcache
import uvicorn
import webview
from dotenv import load_dotenv

from raid_autoupgrade.api.app import create_app
from raid_autoupgrade.detection.progress_bar_detector import ProgressBarStateDetector
from raid_autoupgrade.jobs.run_fn import make_count_runner, make_spend_runner
from raid_autoupgrade.services.cache_service import CacheService
from raid_autoupgrade.services.network import NetworkManager
from raid_autoupgrade.services.screenshot_service import ScreenshotService
from raid_autoupgrade.services.settings_service import SettingsService
from raid_autoupgrade.services.window_interaction_service import (
    WindowInteractionService,
)

load_dotenv()

_HOST = "127.0.0.1"
_PORT = int(os.getenv("RAID_AUTOUPGRADE_API_PORT", "8765"))
_VITE_PORT = int(os.getenv("RAID_AUTOUPGRADE_VITE_PORT", "5173"))
_DEV_URL = f"http://localhost:{_VITE_PORT}"
_DIST_DIR = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"
_SETTINGS_CACHE_DIR = (
    Path(os.getenv("PROGRAMDATA", "C:\\ProgramData")) / "RaidAutoupgrade" / "settings"
)
_REGIONS_CACHE_DIR = (
    Path(os.getenv("LOCALAPPDATA", "C:\\Users\\Default\\AppData\\Local"))
    / "RaidAutoupgrade"
    / "regions"
)


def start(debug: bool = False) -> None:
    dev_mode = os.environ.get("RAID_AUTOUPGRADE_DEV") == "1"

    window_service = WindowInteractionService()
    screenshot_service = ScreenshotService(window_interaction_service=window_service)
    network_manager = NetworkManager()
    regions_cache = diskcache.Cache(directory=str(_REGIONS_CACHE_DIR))
    cache_service = CacheService(cache=regions_cache)
    _debug_root = (
        Path(os.getenv("PROGRAMDATA", "C:\\ProgramData")) / "RaidAutoupgrade" / "debug"
    )
    settings_cache = diskcache.Cache(directory=str(_SETTINGS_CACHE_DIR))
    settings_service = SettingsService(cache=settings_cache)
    detector = ProgressBarStateDetector()

    count_runner = make_count_runner(
        cache_service=cache_service,
        window_service=window_service,
        network_manager=network_manager,
        screenshot_service=screenshot_service,
        detector=detector,
        debug_dir_root=_debug_root,
        settings_service=settings_service,
    )
    spend_runner = make_spend_runner(
        cache_service=cache_service,
        window_service=window_service,
        network_manager=network_manager,
        screenshot_service=screenshot_service,
        detector=detector,
        debug_dir_root=_debug_root,
    )

    app = create_app(
        window_service=window_service,
        network_manager=network_manager,
        count_runner=count_runner,
        spend_runner=spend_runner,
        settings_service=settings_service,
        screenshot_service=screenshot_service,
        cache_service=cache_service,
    )

    if not dev_mode:
        from fastapi.staticfiles import StaticFiles

        app.mount("/", StaticFiles(directory=str(_DIST_DIR), html=True), name="static")

    config = uvicorn.Config(app, host=_HOST, port=_PORT, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    while not server.started:
        time.sleep(0.05)

    url = _DEV_URL if dev_mode else f"http://{_HOST}:{_PORT}"
    webview.create_window("Raid Autoupgrade", url, width=1216, height=832)
    webview.start(debug=debug)
