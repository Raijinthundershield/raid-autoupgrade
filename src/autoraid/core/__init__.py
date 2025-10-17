"""Core domain logic for AutoRaid upgrade automation."""

from autoraid.core.state_machine import (
    UpgradeStateMachine,
    StopCountReason,
    ProgressBarState,
)
from autoraid.core.progress_bar import get_progress_bar_state
from autoraid.core.locate_region import (
    locate_progress_bar,
    locate_upgrade_button,
    MissingRegionException,
)

__all__ = [
    "UpgradeStateMachine",
    "StopCountReason",
    "ProgressBarState",
    "get_progress_bar_state",
    "locate_progress_bar",
    "locate_upgrade_button",
    "MissingRegionException",
]
