"""Windows admin privilege detection and UAC elevation.

This module provides utilities for checking if the current process has administrator
privileges and requesting elevation via UAC (User Account Control) prompt.

Windows-only functionality using ctypes to call Win32 API functions.
"""

import ctypes
import sys
from typing import NoReturn


def is_admin() -> bool:
    """Check if the current process has administrator privileges.

    Uses Windows API IsUserAnAdmin() to determine admin status.

    Returns:
        True if running with admin privileges, False otherwise.

    Note:
        Windows-only. Returns False on any error (defensive fallback).
    """
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        # Defensive fallback: assume non-admin if check fails
        return False


def request_admin() -> NoReturn:
    """Request administrator privileges via UAC prompt and re-launch process.

    Uses Windows API ShellExecuteW with "runas" verb to trigger UAC elevation.
    The current process terminates after launching the elevated process.

    Raises:
        SystemExit: Always exits after re-launching with admin privileges.

    Example:
        >>> if not is_admin():
        ...     request_admin()  # UAC prompt appears, process re-launches elevated
    """
    # Re-launch current script with admin privileges via UAC
    ctypes.windll.shell32.ShellExecuteW(
        None,  # hwnd: no parent window
        "runas",  # operation: run as administrator
        sys.executable,  # file: Python interpreter
        " ".join(sys.argv),  # parameters: script path and arguments
        None,  # directory: use current directory
        1,  # show: SW_SHOWNORMAL (normal window state)
    )

    # Terminate original process (elevated process continues)
    sys.exit()
