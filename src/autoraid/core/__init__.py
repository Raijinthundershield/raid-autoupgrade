"""Core domain logic for AutoRaid upgrade automation."""

from autoraid.core.state_machine import (
    UpgradeStateMachine,
    StopCountReason,  # Backward compatibility alias
    StopReason,
    UpgradeAttemptMonitor,
)
from autoraid.core.progress_bar import ProgressBarState, get_progress_bar_state
from autoraid.core.progress_bar_detector import ProgressBarStateDetector
from autoraid.core.locate_region import (
    locate_progress_bar,
    locate_upgrade_button,
    MissingRegionException,
)

__all__ = [
    "UpgradeStateMachine",
    "StopCountReason",  # Backward compatibility alias
    "StopReason",
    "ProgressBarState",
    "ProgressBarStateDetector",
    "UpgradeAttemptMonitor",
    "get_progress_bar_state",
    "locate_progress_bar",
    "locate_upgrade_button",
    "MissingRegionException",
]
