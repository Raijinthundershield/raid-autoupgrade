"""Computer vision detection algorithms."""

from raid_autoupgrade.detection.locate_region import (
    MissingRegionException,
    locate_artifact_icon,
    locate_instant_upgrade_tickbox,
    locate_progress_bar,
    locate_region,
    locate_upgrade_button,
)
from raid_autoupgrade.detection.progress_bar_detector import (
    ProgressBarState,
    ProgressBarStateDetector,
)

__all__ = [
    "ProgressBarStateDetector",
    "ProgressBarState",
    "MissingRegionException",
    "locate_region",
    "locate_upgrade_button",
    "locate_progress_bar",
    "locate_artifact_icon",
    "locate_instant_upgrade_tickbox",
]
