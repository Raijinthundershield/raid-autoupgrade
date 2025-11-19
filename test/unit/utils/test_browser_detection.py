"""Unit tests for browser detection utilities."""

from pathlib import Path
from unittest.mock import patch

from autoraid.utils.browser_detection import detect_browser, is_edge_browser


class TestDetectBrowser:
    """Unit tests for detect_browser() function."""

    def test_detect_browser_with_chrome_available(self):
        """Verify detect_browser() returns Chrome path when Chrome is available."""
        with patch("shutil.which") as mock_which:
            # Mock Chrome available
            mock_which.side_effect = lambda name: (
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
                if name == "chrome"
                else None
            )

            result = detect_browser()

            assert result == Path(
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
            )

    def test_detect_browser_with_only_edge_available(self):
        """Verify detect_browser() returns Edge path when only Edge is available."""
        with patch("shutil.which") as mock_which:
            # Mock Chrome not available, Edge available
            mock_which.side_effect = lambda name: (
                "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
                if name == "msedge"
                else None
            )

            result = detect_browser()

            assert result == Path(
                "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
            )

    def test_detect_browser_with_neither_available(self):
        """Verify detect_browser() returns None when neither Chrome nor Edge found."""
        with patch("shutil.which", return_value=None):
            result = detect_browser()

            assert result is None

    def test_detect_browser_with_env_var_set(self):
        """Verify detect_browser() uses AUTORAID_BROWSER_PATH env var when set."""
        custom_path = "C:\\custom\\browser.exe"

        with (
            patch("os.getenv", return_value=custom_path),
            patch("pathlib.Path.exists", return_value=True),
            patch("shutil.which", return_value=None),
        ):
            result = detect_browser()

            assert result == Path(custom_path)

    def test_detect_browser_ignores_invalid_env_var(self):
        """Verify detect_browser() falls back to auto-detection if env var path invalid."""
        with (
            patch("os.getenv", return_value="C:\\nonexistent\\browser.exe"),
            patch("pathlib.Path.exists", return_value=False),
            patch("shutil.which") as mock_which,
        ):
            # Mock Chrome available
            mock_which.side_effect = lambda name: (
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
                if name == "chrome"
                else None
            )

            result = detect_browser()

            # Should fall back to Chrome detection
            assert result == Path(
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
            )


class TestIsEdgeBrowser:
    """Unit tests for is_edge_browser() function."""

    def test_is_edge_browser_with_edge_path_returns_true(self):
        """Verify is_edge_browser() returns True for Edge executable path."""
        edge_path = Path(
            "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
        )

        assert is_edge_browser(edge_path) is True

    def test_is_edge_browser_with_chrome_path_returns_false(self):
        """Verify is_edge_browser() returns False for Chrome executable path."""
        chrome_path = Path("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe")

        assert is_edge_browser(chrome_path) is False

    def test_is_edge_browser_with_none_returns_false(self):
        """Verify is_edge_browser() returns False when browser_path is None."""
        assert is_edge_browser(None) is False

    def test_is_edge_browser_case_insensitive(self):
        """Verify is_edge_browser() detects Edge case-insensitively."""
        # Test various Edge path formats
        assert is_edge_browser(Path("C:\\path\\to\\MSEDGE.EXE")) is True
        assert is_edge_browser(Path("C:\\path\\to\\Edge.exe")) is True
        assert is_edge_browser(Path("C:\\path\\to\\msedge")) is True
