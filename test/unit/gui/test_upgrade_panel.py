"""Smoke tests for upgrade panel component."""

from unittest.mock import Mock


from autoraid.gui.components.upgrade_panel import create_upgrade_panel
from autoraid.workflows.count_workflow import CountWorkflow
from autoraid.workflows.spend_workflow import SpendWorkflow


def test_create_upgrade_panel_smoke():
    """Verify panel creation with mocked workflow factories (smoke test)."""
    # Create mock workflow factories
    mock_count_factory = Mock(spec=CountWorkflow)
    mock_spend_factory = Mock(spec=SpendWorkflow)

    # Create panel with mocked dependencies
    create_upgrade_panel(
        count_workflow_factory=mock_count_factory,
        spend_workflow_factory=mock_spend_factory,
    )
    # No exception = pass
