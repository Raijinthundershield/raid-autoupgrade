"""Upgrade orchestrator interface protocol."""

from typing import Protocol
from .upgrade_state_machine import StopCountReason


class UpgradeOrchestratorProtocol(Protocol):
    """Interface for upgrade workflow orchestration."""

    def count_workflow(
        self, network_adapter_id: list[int] | None = None, max_attempts: int = 100
    ) -> tuple[int, StopCountReason]:
        """Execute count workflow and return (fail_count, stop_reason).

        Workflow steps:
        1. Disable network adapters (if specified)
        2. Check Raid window exists
        3. Capture screenshot
        4. Get upgrade regions (cached or detected)
        5. Click upgrade button
        6. Monitor progress bar and count failures
        7. Re-enable network adapters (always, via finally block)

        Args:
            network_adapter_id: List of adapter IDs to disable (None = don't modify network)
            max_attempts: Maximum fail count before stopping

        Returns:
            Tuple of (fail_count, stop_reason)

        Raises:
            WindowNotFoundException: If Raid window not found
            RegionDetectionError: If region detection fails
        """
        ...

    def spend_workflow(
        self, fail_count: int, max_attempts: int, continue_upgrade: bool = False
    ) -> dict:
        """Execute spend workflow and return result summary.

        Workflow steps:
        1. Enable network adapters
        2. Check Raid window exists
        3. Capture screenshot
        4. Get upgrade regions
        5. Loop fail_count times: Click upgrade button → Wait → (Continue if specified)

        Args:
            fail_count: Number of upgrade attempts to spend
            max_attempts: Maximum attempts before stopping (safety limit)
            continue_upgrade: If True, click through upgrade success popups

        Returns:
            Dictionary with keys: spent (int), success (bool)

        Raises:
            WindowNotFoundException: If Raid window not found
            RegionDetectionError: If region detection fails
        """
        ...
