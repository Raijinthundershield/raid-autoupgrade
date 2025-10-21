"""Smoke tests for upgrade panel component."""

from unittest.mock import Mock


from autoraid.gui.components.upgrade_panel import create_upgrade_panel
from autoraid.services.upgrade_orchestrator import UpgradeOrchestrator


def test_create_upgrade_panel_smoke():
    """Verify panel creation with mocked orchestrator (smoke test)."""
    # Create mock orchestrator
    mock_orchestrator = Mock(spec=UpgradeOrchestrator)

    # Create panel with mocked dependency
    create_upgrade_panel(orchestrator=mock_orchestrator)
    # No exception = pass
