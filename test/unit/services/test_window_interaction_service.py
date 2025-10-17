"""Smoke tests for WindowInteractionService.

These tests verify basic functionality of the WindowInteractionService:
- Service instantiation
- Window existence validation
"""

import pytest

from autoraid.services.window_interaction_service import (
    WindowInteractionService,
)


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
