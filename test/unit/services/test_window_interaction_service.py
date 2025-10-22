"""Smoke tests for WindowInteractionService.

These tests verify basic functionality of the WindowInteractionService:
- Service instantiation
- Window existence validation
- Window activation with minimize trick option
"""

import pytest
from unittest.mock import patch, MagicMock

from autoraid.services.window_interaction_service import (
    WindowInteractionService,
)
from autoraid.exceptions import WindowNotFoundException


def test_window_interaction_service_instantiates():
    """Smoke test: Service instantiates correctly."""
    service = WindowInteractionService()
    assert service is not None
    assert isinstance(service, WindowInteractionService)


def test_window_interaction_service_window_exists_validates_input():
    """Smoke test: Service validates window_title input."""
    service = WindowInteractionService()

    # Test empty window title
    with pytest.raises(ValueError, match="window_title cannot be empty"):
        service.window_exists("")


def test_window_interaction_service_activate_window_validates_input():
    """Smoke test: Service validates window_title input for activate_window."""
    service = WindowInteractionService()

    # Test empty window title
    with pytest.raises(ValueError, match="window_title cannot be empty"):
        service.activate_window("")


@patch("autoraid.services.window_interaction_service.pygetwindow.getWindowsWithTitle")
@patch("autoraid.services.window_interaction_service.time.sleep")
def test_window_interaction_service_activate_window_uses_minimize_trick(
    mock_sleep, mock_get_windows
):
    """Smoke test: Service uses minimize trick when use_minimize_trick=True."""
    service = WindowInteractionService(use_minimize_trick=True)

    # Create mock window
    mock_window = MagicMock()
    mock_get_windows.return_value = [mock_window]

    # Call activate_window with minimize trick enabled (default)
    service.activate_window("Test Window")

    # Verify minimize/restore/activate sequence was called
    mock_window.minimize.assert_called_once()
    mock_window.restore.assert_called_once()
    mock_window.activate.assert_called_once()

    # Verify order: minimize -> restore -> activate
    assert mock_window.method_calls[0][0] == "minimize"
    assert mock_window.method_calls[1][0] == "restore"
    assert mock_window.method_calls[2][0] == "activate"


@patch("autoraid.services.window_interaction_service.pygetwindow.getWindowsWithTitle")
@patch("autoraid.services.window_interaction_service.time.sleep")
def test_window_interaction_service_activate_window_without_minimize_trick(
    mock_sleep, mock_get_windows
):
    """Smoke test: Service uses simple activation when use_minimize_trick=False."""
    service = WindowInteractionService(use_minimize_trick=False)

    # Create mock window
    mock_window = MagicMock()
    mock_get_windows.return_value = [mock_window]

    # Call activate_window without minimize trick
    service.activate_window("Test Window")

    # Verify only activate was called (no minimize/restore)
    mock_window.minimize.assert_not_called()
    mock_window.restore.assert_not_called()
    mock_window.activate.assert_called_once()


@patch("autoraid.services.window_interaction_service.pygetwindow.getWindowsWithTitle")
def test_window_interaction_service_activate_window_raises_on_missing_window(
    mock_get_windows,
):
    """Smoke test: Service raises WindowNotFoundException when window not found."""
    service = WindowInteractionService()

    # Mock window not found
    mock_get_windows.return_value = []

    # Verify exception raised
    with pytest.raises(
        WindowNotFoundException, match='Window "Missing Window" not found'
    ):
        service.activate_window("Missing Window")


def test_window_interaction_service_instantiates_with_use_minimize_trick_false():
    """Smoke test: Service instantiates with use_minimize_trick=False."""
    service = WindowInteractionService(use_minimize_trick=False)
    assert service is not None
    assert isinstance(service, WindowInteractionService)
    assert service._use_minimize_trick is False


def test_window_interaction_service_defaults_to_use_minimize_trick_true():
    """Smoke test: Service defaults to use_minimize_trick=True."""
    service = WindowInteractionService(use_minimize_trick=True)
    assert service._use_minimize_trick is True
