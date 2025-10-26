"""Core domain logic for AutoRaid upgrade automation."""

from autoraid.core.stop_conditions import StopReason
from autoraid.core.progress_bar_detector import (
    ProgressBarState,
    ProgressBarStateDetector,
)
from autoraid.core.progress_bar_monitor import (
    ProgressBarMonitor,
    ProgressBarMonitorState,
)
from autoraid.core.locate_region import (
    locate_progress_bar,
    locate_upgrade_button,
    MissingRegionException,
)

__all__ = [
    "StopReason",
    "ProgressBarState",
    "ProgressBarStateDetector",
    "ProgressBarMonitor",
    "ProgressBarMonitorState",
    "locate_progress_bar",
    "locate_upgrade_button",
    "MissingRegionException",
]
