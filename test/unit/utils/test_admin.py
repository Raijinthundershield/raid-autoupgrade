"""Smoke tests for Windows admin privilege utilities."""

from unittest.mock import MagicMock, patch

from autoraid.utils.admin import is_admin, request_admin


class TestIsAdmin:
    """Smoke tests for is_admin() function."""

    def test_is_admin_returns_true_when_user_is_admin(self):
        """Verify is_admin() returns True when IsUserAnAdmin() returns non-zero."""
        with patch("ctypes.windll.shell32.IsUserAnAdmin", return_value=1):
            assert is_admin() is True

    def test_is_admin_returns_false_when_user_is_not_admin(self):
        """Verify is_admin() returns False when IsUserAnAdmin() returns zero."""
        with patch("ctypes.windll.shell32.IsUserAnAdmin", return_value=0):
            assert is_admin() is False

    def test_is_admin_returns_false_on_exception(self):
        """Verify is_admin() returns False (defensive fallback) when API call fails."""
        with patch(
            "ctypes.windll.shell32.IsUserAnAdmin", side_effect=Exception("API error")
        ):
            assert is_admin() is False


class TestRequestAdmin:
    """Smoke tests for request_admin() function."""

    def test_request_admin_calls_shell_execute_with_correct_parameters(self):
        """Verify request_admin() calls ShellExecuteW with correct runas parameters."""
        mock_shell_execute = MagicMock()

        with (
            patch("ctypes.windll.shell32.ShellExecuteW", mock_shell_execute),
            patch("sys.exit") as mock_exit,
            patch("sys.executable", "python.exe"),
            patch("sys.argv", ["script.py", "--flag"]),
        ):
            request_admin()

            # Verify ShellExecuteW called with correct parameters
            mock_shell_execute.assert_called_once_with(
                None,  # hwnd
                "runas",  # operation
                "python.exe",  # file
                "script.py --flag",  # parameters
                None,  # directory
                1,  # show
            )

            # Verify sys.exit() called to terminate original process
            mock_exit.assert_called_once()
