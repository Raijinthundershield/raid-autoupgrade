"""Browser detection utilities for NiceGUI native application.

This module provides utilities for detecting which browser NiceGUI will use when
launching in native mode. NiceGUI follows Chrome → Edge fallback order.

Used to determine if Edge-specific configuration (user data directory) is needed
to avoid permission errors when running with administrator privileges.
"""

import os
import shutil
from pathlib import Path


def detect_browser() -> Path | None:
    """Detect which browser executable NiceGUI will use.

    Detection order (matches NiceGUI's fallback logic):
    1. AUTORAID_BROWSER_PATH environment variable (testing override)
    2. Chrome (via shutil.which('chrome'))
    3. Edge (via shutil.which('msedge'))
    4. None (NiceGUI will fall back to system default)

    Returns:
        Path to detected browser executable, or None if not found.

    Example:
        >>> browser = detect_browser()
        >>> if browser:
        ...     print(f"Will use: {browser}")
    """
    # Check environment variable override (testing only)
    browser_env = os.getenv("AUTORAID_BROWSER_PATH")
    if browser_env:
        browser_path = Path(browser_env)
        if browser_path.exists():
            return browser_path
        # Invalid path in env var - ignore and continue with auto-detection

    # Check Chrome (NiceGUI's first choice)
    chrome_path = shutil.which("chrome")
    if chrome_path:
        return Path(chrome_path)

    # Check Edge (NiceGUI's fallback)
    edge_path = shutil.which("msedge")
    if edge_path:
        return Path(edge_path)

    # Neither found - NiceGUI will use system default
    return None


def is_edge_browser(browser_path: Path | None) -> bool:
    """Check if the given browser path is Microsoft Edge.

    Args:
        browser_path: Path to browser executable (from detect_browser()).

    Returns:
        True if browser is Edge/msedge, False otherwise.

    Example:
        >>> browser = detect_browser()
        >>> if is_edge_browser(browser):
        ...     # Apply Edge-specific configuration
        ...     pass
    """
    if browser_path is None:
        return False

    # Check if path contains 'edge' or 'msedge' (case-insensitive)
    browser_name = browser_path.name.lower()
    return "edge" in browser_name or "msedge" in browser_name
