"""Service interface protocols for AutoRaid refactoring."""

from .cache_service import CacheServiceProtocol
from .screenshot_service import ScreenshotServiceProtocol
from .locate_region_service import LocateRegionServiceProtocol
from .window_interaction_service import WindowInteractionServiceProtocol
from .upgrade_state_machine import (
    ProgressBarState,
    StopCountReason,
    UpgradeStateMachineProtocol,
)
from .upgrade_orchestrator import UpgradeOrchestratorProtocol

__all__ = [
    "CacheServiceProtocol",
    "ScreenshotServiceProtocol",
    "LocateRegionServiceProtocol",
    "WindowInteractionServiceProtocol",
    "ProgressBarState",
    "StopCountReason",
    "UpgradeStateMachineProtocol",
    "UpgradeOrchestratorProtocol",
]
