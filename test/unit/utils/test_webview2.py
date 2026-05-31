"""Unit tests for the WebView2 runtime detector."""

from raid_autoupgrade.utils.webview2 import _HIVES, webview2_installed

# (HKLM, HKCU) hive handles the detector iterates. Sourced from the module
# rather than winreg so this pure-logic test runs cross-platform (winreg is
# Windows-only); the stub treats them as opaque keys.
_HKLM, _HKCU = _HIVES


class _RegistryStub:
    """Stub registry reader keyed by hive.

    Substitutes the real winreg-backed reader at the detector's boundary,
    returning the configured ``pv`` value for a hive (or None if absent).
    """

    def __init__(self, pv_by_hive: dict[int, str | None]) -> None:
        self._pv_by_hive = pv_by_hive

    def __call__(self, hive: int, subkey: str, value_name: str) -> str | None:
        return self._pv_by_hive.get(hive)


class TestWebview2Installed:
    """Contract: detect WebView2 from the EdgeUpdate client key in either hive."""

    def test_true_when_hklm_has_non_empty_version(self):
        reader = _RegistryStub({_HKLM: "121.0.2277.83"})

        assert webview2_installed(reader) is True

    def test_false_when_absent_in_both_hives(self):
        reader = _RegistryStub({})

        assert webview2_installed(reader) is False

    def test_true_when_present_only_under_hkcu(self):
        reader = _RegistryStub({_HKCU: "121.0.2277.83"})

        assert webview2_installed(reader) is True

    def test_false_when_version_is_empty(self):
        reader = _RegistryStub({_HKLM: ""})

        assert webview2_installed(reader) is False
