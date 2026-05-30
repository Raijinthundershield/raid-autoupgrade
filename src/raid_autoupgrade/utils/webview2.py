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
    """Read a registry string value via winreg, or None if absent.

    Tries both the 32-bit and 64-bit registry views and returns the value from
    whichever has it. WebView2's location depends on the install type and OS
    architecture: a per-machine install on 64-bit Windows lands in the 32-bit
    view (``WOW6432Node``, because EdgeUpdate is a 32-bit process), while a
    per-user install or a 32-bit OS uses the native view. A 64-bit process that
    reads only its default view therefore misses the common per-machine case
    and wrongly reports the runtime absent. Checking both views covers every
    documented location without relying on which one applies.
    """
    for view in (winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
        try:
            with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ | view) as key:
                value, _ = winreg.QueryValueEx(key, value_name)
        except OSError:
            continue
        if isinstance(value, str):
            return value
    return None


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
