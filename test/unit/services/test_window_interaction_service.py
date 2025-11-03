"""Unit tests for WindowInteractionService."""

import ctypes
from unittest.mock import Mock, patch

import pytest

from autoraid.exceptions import WindowNotFoundException
from autoraid.services.window_interaction_service import (
    WindowInteractionService,
    SW_MINIMIZE,
    SW_RESTORE,
)


class TestWindowInteractionService:
    """Test suite for WindowInteractionService."""

    @pytest.fixture
    def service(self):
        """Create a WindowInteractionService instance for testing."""
        return WindowInteractionService()

    @pytest.fixture
    def mock_window(self):
        """Create a mock window object."""
        window = Mock()
        window.title = "Test Window"
        window._hWnd = 12345  # Mock HWND
        window.isActive = False
        window.isMinimized = False
        window.left = 100
        window.top = 100
        window.width = 800
        window.height = 600
        window.height = 600  # For get_window_size return value
        return window

    # Test window_exists
    def test_window_exists_returns_true_when_window_found(self, service, mock_window):
        """Test that window_exists returns True when window is found."""
        with patch("pygetwindow.getAllWindows", return_value=[mock_window]):
            assert service.window_exists("Test Window") is True

    def test_window_exists_returns_false_when_window_not_found(self, service):
        """Test that window_exists returns False when window not found."""
        mock_other_window = Mock()
        mock_other_window.title = "Other Window"

        with patch("pygetwindow.getAllWindows", return_value=[mock_other_window]):
            assert service.window_exists("Test Window") is False

    def test_window_exists_returns_false_when_no_windows(self, service):
        """Test that window_exists returns False when no windows exist."""
        with patch("pygetwindow.getAllWindows", return_value=[]):
            assert service.window_exists("Test Window") is False

    def test_window_exists_raises_error_on_empty_title(self, service):
        """Test that window_exists raises ValueError for empty title."""
        with pytest.raises(ValueError, match="window_title cannot be empty"):
            service.window_exists("")

    # Test get_window_size
    def test_get_window_size_returns_correct_dimensions(self, service, mock_window):
        """Test that get_window_size returns correct height and width using GetWindowPlacement."""
        from autoraid.services.window_interaction_service import WINDOWPLACEMENT

        # Create actual WINDOWPLACEMENT structure
        def mock_get_window_placement_side_effect(hwnd, placement_byref):
            # Get the actual WINDOWPLACEMENT object from byref
            # We need to cast the pointer back to get the object
            placement_ptr = ctypes.cast(
                placement_byref, ctypes.POINTER(WINDOWPLACEMENT)
            )
            placement = placement_ptr.contents

            # Set the restored rectangle
            placement.rcNormalPosition.left = 100
            placement.rcNormalPosition.top = 50
            placement.rcNormalPosition.right = 900  # width = 800
            placement.rcNormalPosition.bottom = 650  # height = 600
            return True

        service._user32.GetWindowPlacement = Mock(
            side_effect=mock_get_window_placement_side_effect
        )

        with patch("pygetwindow.getWindowsWithTitle", return_value=[mock_window]):
            height, width = service.get_window_size("Test Window")
            assert height == 600
            assert width == 800
            service._user32.GetWindowPlacement.assert_called_once()

    def test_get_window_size_returns_restored_size_when_minimized(
        self, service, mock_window
    ):
        """Test that get_window_size returns restored size even when window is minimized."""
        from autoraid.services.window_interaction_service import WINDOWPLACEMENT

        # Create actual WINDOWPLACEMENT structure with restored dimensions
        def mock_get_window_placement_side_effect(hwnd, placement_byref):
            placement_ptr = ctypes.cast(
                placement_byref, ctypes.POINTER(WINDOWPLACEMENT)
            )
            placement = placement_ptr.contents

            # Restored rectangle remains constant regardless of minimized state
            placement.rcNormalPosition.left = 100
            placement.rcNormalPosition.top = 50
            placement.rcNormalPosition.right = 1328  # width = 1228
            placement.rcNormalPosition.bottom = 768  # height = 718
            return True

        service._user32.GetWindowPlacement = Mock(
            side_effect=mock_get_window_placement_side_effect
        )
        mock_window.isMinimized = True  # Window is minimized

        with patch("pygetwindow.getWindowsWithTitle", return_value=[mock_window]):
            height, width = service.get_window_size("Test Window")
            # Should return restored size (718x1228), NOT minimized size (28x160)
            assert height == 718
            assert width == 1228
            service._user32.GetWindowPlacement.assert_called_once()

    def test_get_window_size_raises_error_when_window_not_found(self, service):
        """Test that get_window_size raises WindowNotFoundException."""
        with patch("pygetwindow.getWindowsWithTitle", return_value=[]):
            with pytest.raises(WindowNotFoundException):
                service.get_window_size("Test Window")

    def test_get_window_size_raises_error_on_empty_title(self, service):
        """Test that get_window_size raises ValueError for empty title."""
        with pytest.raises(ValueError, match="window_title cannot be empty"):
            service.get_window_size("")

    def test_get_window_size_raises_error_on_get_window_placement_failure(
        self, service, mock_window
    ):
        """Test that get_window_size raises RuntimeError when GetWindowPlacement fails."""
        mock_user32 = Mock()
        mock_user32.GetWindowPlacement.return_value = False  # API call failed
        service._user32 = mock_user32

        with patch("pygetwindow.getWindowsWithTitle", return_value=[mock_window]):
            with pytest.raises(RuntimeError, match="GetWindowPlacement failed"):
                service.get_window_size("Test Window")

    # Test _get_hwnd
    def test_get_hwnd_returns_window_handle(self, service, mock_window):
        """Test that _get_hwnd returns the window handle."""
        with patch("pygetwindow.getWindowsWithTitle", return_value=[mock_window]):
            hwnd = service._get_hwnd("Test Window")
            assert hwnd == 12345

    def test_get_hwnd_raises_error_when_window_not_found(self, service):
        """Test that _get_hwnd raises WindowNotFoundException."""
        with patch("pygetwindow.getWindowsWithTitle", return_value=[]):
            with pytest.raises(WindowNotFoundException):
                service._get_hwnd("Test Window")

    # Test _activate_with_alt_key
    def test_activate_with_alt_key_succeeds(self, service):
        """Test ALT key activation strategy succeeds."""
        mock_user32 = Mock()
        mock_user32.SendInput.return_value = 2  # Success
        mock_user32.SetForegroundWindow.return_value = True
        service._user32 = mock_user32

        result = service._activate_with_alt_key(12345)

        assert result is True
        mock_user32.SendInput.assert_called_once()
        mock_user32.SetForegroundWindow.assert_called_once_with(12345)

    def test_activate_with_alt_key_fails_on_send_input_error(self, service):
        """Test ALT key activation fails when SendInput returns 0."""
        mock_user32 = Mock()
        mock_user32.SendInput.return_value = 0  # Failure
        service._user32 = mock_user32

        result = service._activate_with_alt_key(12345)

        assert result is False
        mock_user32.SetForegroundWindow.assert_not_called()

    def test_activate_with_alt_key_fails_on_set_foreground_error(self, service):
        """Test ALT key activation fails when SetForegroundWindow fails."""
        mock_user32 = Mock()
        mock_user32.SendInput.return_value = 2  # Success
        mock_user32.SetForegroundWindow.return_value = False
        service._user32 = mock_user32

        result = service._activate_with_alt_key(12345)

        assert result is False

    def test_activate_with_alt_key_handles_exception(self, service):
        """Test ALT key activation handles exceptions gracefully."""
        mock_user32 = Mock()
        mock_user32.SendInput.side_effect = Exception("Test error")
        service._user32 = mock_user32

        result = service._activate_with_alt_key(12345)

        assert result is False

    # Test _activate_with_minimize_trick
    def test_activate_with_minimize_trick_succeeds(self, service):
        """Test minimize trick activation strategy succeeds."""
        mock_user32 = Mock()
        mock_user32.ShowWindow.return_value = True
        mock_user32.SetForegroundWindow.return_value = True
        service._user32 = mock_user32

        result = service._activate_with_minimize_trick(12345)

        assert result is True
        # Verify minimize and restore were called
        calls = mock_user32.ShowWindow.call_args_list
        assert len(calls) == 2
        assert calls[0][0] == (12345, SW_MINIMIZE)
        assert calls[1][0] == (12345, SW_RESTORE)
        mock_user32.SetForegroundWindow.assert_called_once_with(12345)

    def test_activate_with_minimize_trick_handles_exception(self, service):
        """Test minimize trick handles exceptions gracefully."""
        mock_user32 = Mock()
        mock_user32.ShowWindow.side_effect = Exception("Test error")
        service._user32 = mock_user32

        result = service._activate_with_minimize_trick(12345)

        assert result is False

    # Test activate_window (integration of strategies)
    def test_activate_window_skips_activation_if_already_active(
        self, service, mock_window
    ):
        """Test that activate_window skips activation if window already active."""
        mock_window.isActive = True
        mock_window.isMinimized = False

        with patch("pygetwindow.getWindowsWithTitle", return_value=[mock_window]):
            # Mock all strategy methods to ensure none are called
            service._activate_with_alt_key = Mock()
            service._activate_with_thread_attach = Mock()
            service._activate_with_minimize_trick = Mock()

            service.activate_window("Test Window")

            # Verify no activation strategies were attempted
            service._activate_with_alt_key.assert_not_called()
            service._activate_with_thread_attach.assert_not_called()
            service._activate_with_minimize_trick.assert_not_called()

    def test_activate_window_restores_minimized_window_after_activation(
        self, service, mock_window
    ):
        """Test that activate_window restores window from minimized state after activation."""
        # Window starts minimized
        mock_window.isMinimized = True
        mock_window.isActive = False

        # Create a second mock for post-activation check
        mock_window_after = Mock()
        mock_window_after.isMinimized = True  # Still minimized after activation

        call_count = [0]

        def get_windows_side_effect(title):
            call_count[0] += 1
            if call_count[0] == 1:
                return [mock_window]  # First call (before activation)
            else:
                return [mock_window_after]  # Second call (after activation check)

        with patch(
            "pygetwindow.getWindowsWithTitle", side_effect=get_windows_side_effect
        ):
            service._activate_with_alt_key = Mock(return_value=True)
            mock_user32 = Mock()
            service._user32 = mock_user32

            service.activate_window("Test Window")

            # Verify activation was attempted
            service._activate_with_alt_key.assert_called_once_with(12345)

            # Verify ShowWindow was called to restore
            mock_user32.ShowWindow.assert_called_once_with(12345, 9)  # SW_RESTORE = 9

    def test_activate_window_succeeds_with_alt_key_strategy(self, service, mock_window):
        """Test activate_window succeeds with ALT key strategy."""
        with patch("pygetwindow.getWindowsWithTitle", return_value=[mock_window]):
            service._activate_with_alt_key = Mock(return_value=True)
            service._activate_with_thread_attach = Mock()
            service._activate_with_minimize_trick = Mock()

            service.activate_window("Test Window")

            # Verify only ALT key strategy was tried
            service._activate_with_alt_key.assert_called_once_with(12345)
            service._activate_with_minimize_trick.assert_not_called()

    def test_activate_window_falls_back_to_minimize_trick(self, service, mock_window):
        """Test activate_window falls back to minimize trick as last resort."""
        with patch("pygetwindow.getWindowsWithTitle", return_value=[mock_window]):
            service._activate_with_alt_key = Mock(return_value=False)
            service._activate_with_minimize_trick = Mock(return_value=True)

            service.activate_window("Test Window")

            # Verify both strategies were tried
            service._activate_with_alt_key.assert_called_once_with(12345)
            service._activate_with_minimize_trick.assert_called_once_with(12345)

    def test_activate_window_raises_error_when_all_strategies_fail(
        self, service, mock_window
    ):
        """Test activate_window raises RuntimeError when all strategies fail."""
        with patch("pygetwindow.getWindowsWithTitle", return_value=[mock_window]):
            service._activate_with_alt_key = Mock(return_value=False)
            service._activate_with_minimize_trick = Mock(return_value=False)

            with pytest.raises(RuntimeError, match="after trying all strategies"):
                service.activate_window("Test Window")

    def test_activate_window_raises_error_when_window_not_found(self, service):
        """Test activate_window raises WindowNotFoundException."""
        with patch("pygetwindow.getWindowsWithTitle", return_value=[]):
            with pytest.raises(WindowNotFoundException):
                service.activate_window("Test Window")

    def test_activate_window_raises_error_on_empty_title(self, service):
        """Test activate_window raises ValueError for empty title."""
        with pytest.raises(ValueError, match="window_title cannot be empty"):
            service.activate_window("")

    # Test click_region
    @patch("pyautogui.click")
    def test_click_region_succeeds(self, mock_click, service, mock_window):
        """Test click_region successfully clicks in window region."""
        with patch("pygetwindow.getWindowsWithTitle", return_value=[mock_window]):
            service.activate_window = Mock()  # Mock activation
            region = (50, 50, 100, 100)

            service.click_region("Test Window", region)

            # Verify window was activated
            service.activate_window.assert_called_once_with("Test Window")

            # Verify click at correct coordinates
            # Center of region (50, 50, 100, 100) = (50 + 50, 50 + 50)
            # Absolute coordinates = (100 + 100, 100 + 100)
            mock_click.assert_called_once_with(200, 200)

    def test_click_region_raises_error_on_invalid_dimensions(self, service):
        """Test click_region raises ValueError for invalid region dimensions."""
        region = (50, 50, 0, 100)  # Invalid width

        with pytest.raises(ValueError, match="Invalid region dimensions"):
            service.click_region("Test Window", region)

    def test_click_region_raises_error_when_window_not_found(self, service):
        """Test click_region raises WindowNotFoundException."""
        with patch("pygetwindow.getWindowsWithTitle", return_value=[]):
            service.activate_window = Mock()
            region = (50, 50, 100, 100)

            with pytest.raises(WindowNotFoundException):
                service.click_region("Test Window", region)

    def test_click_region_raises_error_on_empty_title(self, service):
        """Test click_region raises ValueError for empty title."""
        region = (50, 50, 100, 100)

        with pytest.raises(ValueError, match="window_title cannot be empty"):
            service.click_region("", region)
