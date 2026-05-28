"""pywebview + FastAPI launcher for the AutoRaid GUI.

Starts FastAPI in-process on 127.0.0.1 and opens a native pywebview window.
Dev mode (AUTORAID_DEV=1): window points at the Vite dev server (HMR).
Prod mode: FastAPI serves the built frontend/dist/ as static files.
"""

import os
import threading
import time
from pathlib import Path

import diskcache
import uvicorn
import webview

from autoraid.api.app import create_app
from autoraid.jobs.run_fn import make_count_runner
from autoraid.services.network import NetworkManager
from autoraid.services.settings_service import SettingsService
from autoraid.services.window_interaction_service import WindowInteractionService

_HOST = "127.0.0.1"
_PORT = 8765
_DEV_URL = "http://localhost:5173"
_DIST_DIR = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"
_SETTINGS_CACHE_DIR = (
    Path(os.getenv("PROGRAMDATA", "C:\\ProgramData")) / "AutoRaid" / "settings"
)


def start(debug: bool = False) -> None:
    dev_mode = os.environ.get("AUTORAID_DEV") == "1"

    window_service = WindowInteractionService()
    network_manager = NetworkManager()
    count_runner = make_count_runner(
        cache_service=None,
        window_service=window_service,
        network_manager=network_manager,
        screenshot_service=None,
        detector=None,
    )
    settings_cache = diskcache.Cache(directory=str(_SETTINGS_CACHE_DIR))
    settings_service = SettingsService(cache=settings_cache)

    app = create_app(
        window_service=window_service,
        network_manager=network_manager,
        count_runner=count_runner,
        settings_service=settings_service,
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
    webview.create_window("AutoRaid", url, width=1216, height=832)
    webview.start(debug=debug)
