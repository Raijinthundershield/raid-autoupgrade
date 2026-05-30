"""Detection of the Microsoft Edge WebView2 runtime.

pywebview's Windows backend renders through the Edge WebView2 runtime. It is
preinstalled on current Windows 10/11, but a fresh or stripped machine may lack
it, in which case the window fails to open. ``webview2_installed`` checks the
runtime's registry marker so the app can prompt the user to install it instead
of crashing silently.

The detector reads the ``pv`` (product version) value of the WebView2 Runtime's
EdgeUpdate client key under HKLM (per-machine install) and HKCU (per-user
install). A present, non-empty version marks the runtime as installed.
"""

import winreg
from collections.abc import Callable

RegistryReader = Callable[[int, str, str], "str | None"]
"""Reads a registry string value: ``(hive, subkey, value_name) -> str | None``.

Returns None when the key or value is absent. Injected at the detector boundary
so tests substitute a stub instead of patching ``winreg``.
"""

_CLIENT_KEY = (
    r"SOFTWARE\Microsoft\EdgeUpdate\Clients" r"\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
)
_VERSION_VALUE = "pv"
_HIVES = (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER)


def _winreg_reader(hive: int, subkey: str, value_name: str) -> "str | None":
    """Read a registry string value via winreg, or None if absent."""
    try:
        with winreg.OpenKey(hive, subkey) as key:
            value, _ = winreg.QueryValueEx(key, value_name)
    except OSError:
        return None
    return value if isinstance(value, str) else None


def webview2_installed(read_value: RegistryReader = _winreg_reader) -> bool:
    """Return whether the Edge WebView2 runtime is installed.

    Args:
        read_value: Registry reader injected at the boundary. Defaults to a
            winreg-backed reader.

    Returns:
        True if the runtime's ``pv`` value is present and non-empty in either
        the per-machine (HKLM) or per-user (HKCU) hive.
    """
    for hive in _HIVES:
        version = read_value(hive, _CLIENT_KEY, _VERSION_VALUE)
        if version:
            return True
    return False
