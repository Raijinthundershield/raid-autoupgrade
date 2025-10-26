"""
Debug Monitor workflow implementation.

This module implements a debug workflow for monitoring the progress bar and saving
diagnostic data (screenshots, ROIs, and state metadata) to disk.
"""

from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from autoraid.core.debug_frame_logger import DebugFrameLogger
from autoraid.core.stop_conditions import (
    MaxFramesCondition,
    StopConditionChain,
    StopReason,
)
from autoraid.exceptions import WorkflowValidationError
from autoraid.services.cache_service import CacheService
from autoraid.services.network import NetworkManager, NetworkState
from autoraid.services.upgrade_orchestrator import (
    UpgradeOrchestrator,
    UpgradeSession,
)
from autoraid.services.window_interaction_service import WindowInteractionService


@dataclass(frozen=True)
class DebugMonitorResult:
    """Result from debug monitor workflow."""

    total_frames: int
    output_dir: Path
    stop_reason: StopReason


class DebugMonitorWorkflow:
    """Debug workflow for monitoring progress bar and saving diagnostic data."""

    WINDOW_TITLE = "Raid: Shadow Legends"

    def __init__(
        self,
        orchestrator: UpgradeOrchestrator,
        cache_service: CacheService,
        window_interaction_service: WindowInteractionService,
        network_manager: NetworkManager,
        network_adapter_ids: list[int] | None = None,
        disable_network: bool = True,
        max_frames: int | None = None,
        check_interval: float = 0.2,
        debug_dir: Path | None = None,
    ):
        """Initialize debug monitor workflow.

        Args:
            orchestrator: UpgradeOrchestrator for executing monitoring sessions
            cache_service: CacheService for retrieving cached regions
            window_interaction_service: WindowInteractionService for window operations
            network_manager: NetworkManager for network state validation
            network_adapter_ids: List of adapter IDs to disable/enable
            disable_network: Whether to disable network during monitoring
            max_frames: Maximum frames to capture (None = unlimited)
            check_interval: Time between frame captures in seconds
            debug_dir: Base directory for debug output (None = use default)
        """
        self._orchestrator = orchestrator
        self._cache_service = cache_service
        self._window_interaction_service = window_interaction_service
        self._network_manager = network_manager
        self._network_adapter_ids = network_adapter_ids
        self._disable_network = disable_network
        self._max_frames = max_frames
        self._check_interval = check_interval
        self._debug_dir = debug_dir

    def validate(self) -> None:
        """Validate workflow-specific preconditions.

        Note: Window existence and region cache validation moved to orchestrator.
        This method only validates workflow-specific concerns (network configuration).

        Raises:
            WorkflowValidationError: If network configuration is invalid
        """
        logger.info("Starting debug monitor workflow validation")

        # Network configuration (workflow-specific validation)
        if self._disable_network:
            if (
                self._network_manager.check_network_access() == NetworkState.ONLINE
                and not self._network_adapter_ids
            ):
                raise WorkflowValidationError(
                    "Internet access detected but no network adapter specified. "
                    "Specify adapter IDs with --network-adapter-id or use --keep-network flag."
                )

        logger.info("Debug monitor workflow validation completed successfully")

    def run(self) -> DebugMonitorResult:
        """Execute debug monitor workflow.

        Returns:
            DebugMonitorResult with frame count, output directory, and stop reason

        Raises:
            WindowNotFoundException: If Raid window not found
            WorkflowValidationError: If regions not cached
        """
        logger.info("Starting debug monitor workflow execution")

        # Get regions from cache
        current_size = self._window_interaction_service.get_window_size(
            self.WINDOW_TITLE
        )
        regions = self._cache_service.get_regions(current_size)

        # Configure stop conditions
        stop_conditions = (
            StopConditionChain([MaxFramesCondition(max_frames=self._max_frames)])
            if self._max_frames
            else StopConditionChain([])
        )

        # Create debug logger (always enabled for this workflow)
        output_dir = (
            self._debug_dir
            if self._debug_dir
            else Path("cache-raid-autoupgrade") / "debug"
        )
        debug_logger = DebugFrameLogger(
            output_dir=output_dir / "progressbar_monitor",
            session_name=None,  # Auto-generate timestamp
        )

        # Create session configuration
        session = UpgradeSession(
            upgrade_bar_region=regions["upgrade_bar"],
            upgrade_button_region=regions["upgrade_button"],
            stop_conditions=stop_conditions,
            check_interval=self._check_interval,
            network_adapter_ids=self._network_adapter_ids,
            disable_network=self._disable_network,
            debug_logger=debug_logger,
        )

        # Execute via orchestrator
        try:
            result = self._orchestrator.run_upgrade_session(session)
        except KeyboardInterrupt:
            logger.info("Monitoring interrupted by user")
            # Save what we have so far
            debug_logger.save_summary({"interrupted": True})
            result = None

        logger.info(
            f"Debug monitor workflow completed: "
            f"{debug_logger.frame_count} frames captured"
        )

        return DebugMonitorResult(
            total_frames=debug_logger.frame_count,
            output_dir=debug_logger.session_dir,
            stop_reason=result.stop_reason if result else StopReason.MANUAL_STOP,
        )
