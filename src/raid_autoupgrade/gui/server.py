"""pywebview + FastAPI launcher for the Raid Autoupgrade GUI.

Starts FastAPI in-process on 127.0.0.1 and opens a native pywebview window.
Dev mode (RAID_AUTOUPGRADE_DEV=1): window points at the Vite dev server (HMR).
Prod mode: FastAPI serves the built frontend/dist/ as static files.
"""

import ctypes
import os
import threading
import time
import webbrowser
from pathlib import Path

import diskcache
import uvicorn
import webview
from dotenv import load_dotenv
from loguru import logger

from raid_autoupgrade.api.app import create_app
from raid_autoupgrade.detection.progress_bar_detector import ProgressBarStateDetector
from raid_autoupgrade.jobs.run_fn import make_count_runner, make_spend_runner
from raid_autoupgrade.services.cache_service import CacheService
from raid_autoupgrade.services.count_target_screenshot import CountTargetScreenshot
from raid_autoupgrade.services.debug_session_store import DebugSessionStore
from raid_autoupgrade.services.network import NetworkManager
from raid_autoupgrade.services.screenshot_service import ScreenshotService
from raid_autoupgrade.services.settings_service import SettingsService
from raid_autoupgrade.services.window_interaction_service import (
    WindowInteractionService,
)
from raid_autoupgrade.logging_config import add_logger_sink
from raid_autoupgrade.utils.resources import resource_path
from raid_autoupgrade.utils.webview2 import webview2_installed

load_dotenv()

_HOST = "127.0.0.1"
_PORT = int(os.getenv("RAID_AUTOUPGRADE_API_PORT", "8765"))
_VITE_PORT = int(os.getenv("RAID_AUTOUPGRADE_VITE_PORT", "5173"))
_DEV_URL = f"http://localhost:{_VITE_PORT}"
_DIST_DIR = resource_path("frontend", "dist")
_SETTINGS_CACHE_DIR = (
    Path(os.getenv("PROGRAMDATA", "C:\\ProgramData")) / "RaidAutoupgrade" / "settings"
)
_REGIONS_CACHE_DIR = (
    Path(os.getenv("LOCALAPPDATA", "C:\\Users\\Default\\AppData\\Local"))
    / "RaidAutoupgrade"
    / "regions"
)
# Persists across the offline→online switch and app restarts, like the settings
# (last_count_result) it is paired with.
_COUNT_SCREENSHOT_DIR = (
    Path(os.getenv("PROGRAMDATA", "C:\\ProgramData"))
    / "RaidAutoupgrade"
    / "count_target"
)
_LOG_DIR = (
    Path(os.getenv("PROGRAMDATA", "C:\\ProgramData")) / "RaidAutoupgrade" / "logs"
)
_LOG_FILE = _LOG_DIR / "app.log"
_WEBVIEW2_INSTALL_URL = "https://aka.ms/webview2"

_MB_ICONWARNING = 0x00000030
_MB_ICONERROR = 0x00000010
_MB_TOPMOST = 0x00040000


def _message_box(text: str, title: str, icon: int) -> None:
    """Show a native modal message box (windowed builds have no console)."""
    ctypes.windll.user32.MessageBoxW(None, text, title, icon | _MB_TOPMOST)


def _configure_file_logging(debug: bool) -> None:
    """Replace loguru's default stderr sink with a rotating UTF-8 file sink.

    Loguru installs a default ``sys.stderr`` sink at import. Under ``uv run``
    (and any redirected console) that stream is cp1252, so a log line carrying
    non-ASCII text — e.g. an emoji in a Windows network-adapter name — fails to
    encode; loguru then re-raises while writing its own error report, and the
    UnicodeEncodeError propagates out of the logging call and aborts the
    workflow. Removing the default sink leaves only the UTF-8 file sink.
    """
    logger.remove()
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    add_logger_sink(
        debug=debug,
        sink=str(_LOG_FILE),
        rotation="5 MB",
        retention=3,
        enqueue=True,
    )


def _prompt_install_webview2() -> None:
    """Tell the user the WebView2 runtime is missing and open its download page."""
    logger.error("Edge WebView2 runtime not found; prompting user to install it.")
    _message_box(
        "Raid Autoupgrade needs the Microsoft Edge WebView2 runtime, which was "
        "not found on this PC.\n\nThe download page will now open in your "
        "browser. Install the runtime, then start Raid Autoupgrade again.",
        "WebView2 Runtime Required",
        _MB_ICONWARNING,
    )
    webbrowser.open(_WEBVIEW2_INSTALL_URL)


def _show_fatal_error() -> None:
    """Point the user at the log file after a fatal startup failure."""
    _message_box(
        "Raid Autoupgrade failed to start.\n\n"
        f"Details were written to the log file:\n{_LOG_FILE}",
        "Raid Autoupgrade — Startup Error",
        _MB_ICONERROR,
    )


def start(debug: bool = False) -> None:
    """Launch the GUI with startup hardening.

    Configures a persistent file log, fails gracefully with a message box if the
    WebView2 runtime is missing, and surfaces any fatal startup error to the user
    (a windowed build has no console to print a traceback to).
    """
    _configure_file_logging(debug)

    if not webview2_installed():
        _prompt_install_webview2()
        return

    try:
        _run(debug=debug)
    except Exception:
        logger.exception("Fatal error during GUI startup.")
        _show_fatal_error()
        raise


def _run(debug: bool = False) -> None:
    dev_mode = os.environ.get("RAID_AUTOUPGRADE_DEV") == "1"

    window_service = WindowInteractionService()
    screenshot_service = ScreenshotService(window_interaction_service=window_service)
    network_manager = NetworkManager()
    regions_cache = diskcache.Cache(directory=str(_REGIONS_CACHE_DIR))
    cache_service = CacheService(cache=regions_cache)
    # Debug-frame capture is opt-in via the --debug CLI flag. Without it, no
    # root is wired and workflows write no debug artifacts.
    _debug_root = (
        Path(os.getenv("PROGRAMDATA", "C:\\ProgramData")) / "RaidAutoupgrade" / "debug"
        if debug
        else None
    )
    # Read side of the same debug captures: the Label tab reviews sessions
    # under this root. Disabled (no root) unless launched with --debug.
    debug_session_store = DebugSessionStore(debug_root=_debug_root)
    settings_cache = diskcache.Cache(directory=str(_SETTINGS_CACHE_DIR))
    settings_service = SettingsService(cache=settings_cache)
    count_screenshot_store = CountTargetScreenshot(directory=_COUNT_SCREENSHOT_DIR)
    detector = ProgressBarStateDetector()

    count_runner = make_count_runner(
        cache_service=cache_service,
        window_service=window_service,
        network_manager=network_manager,
        screenshot_service=screenshot_service,
        detector=detector,
        debug_dir_root=_debug_root,
        settings_service=settings_service,
        screenshot_store=count_screenshot_store,
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
        count_screenshot_store=count_screenshot_store,
        debug_session_store=debug_session_store,
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
