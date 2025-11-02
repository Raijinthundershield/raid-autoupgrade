"""Smoke tests for network panel component."""

import sys
from unittest.mock import MagicMock, Mock, patch

# Mock nicegui.native before importing any GUI components
sys.modules["nicegui.native"] = MagicMock()

from autoraid.gui.components.network_panel import create_network_panel  # noqa: E402
from autoraid.services.network import NetworkState  # noqa: E402


def test_create_network_panel_smoke():
    """Verify panel creation without errors.

    This smoke test verifies:
    - Component instantiates without exceptions
    - NetworkManager dependency is used correctly
    - No runtime errors during setup
    """
    # Mock NiceGUI components to avoid requiring a running UI
    with (
        patch("autoraid.gui.components.network_panel.ui") as mock_ui,
        patch("autoraid.gui.components.network_panel.app") as mock_app,
    ):
        # Setup mock storage
        mock_app.storage.user = {}

        # Setup mock network manager instance
        mock_nm = Mock()
        mock_nm.check_network_access.return_value = NetworkState.ONLINE
        mock_nm.get_adapters.return_value = []

        # Setup mock UI components
        mock_ui.column.return_value.__enter__ = Mock()
        mock_ui.column.return_value.__exit__ = Mock(return_value=False)
        mock_ui.row.return_value.__enter__ = Mock()
        mock_ui.row.return_value.__exit__ = Mock(return_value=False)

        # Call with explicit network_manager to bypass DI
        create_network_panel(network_manager=mock_nm)

        # Verify storage was initialized
        assert "selected_adapters" in mock_app.storage.user
        assert mock_app.storage.user["selected_adapters"] == []
