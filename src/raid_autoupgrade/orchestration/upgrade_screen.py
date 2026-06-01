"""The in-game upgrade surface as a deep module.

``UpgradeScreen`` represents the Raid upgrade screen — the surface bearing the
upgrade button and the progress bar. It owns the Raid window title, resolves the
window-size→Regions lookup once at construction, and exposes an intent-named,
coordinate-free interface for driving an attempt and reading the progress bar.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from raid_autoupgrade.constants import RAID_WINDOW_TITLE
from raid_autoupgrade.exceptions import (
    WindowNotFoundException,
    WindowResizedError,
    WorkflowValidationError,
)
from raid_autoupgrade.protocols import (
    CacheProtocol,
    ScreenshotProtocol,
    WindowInteractionProtocol,
)

UPGRADE_BAR = "upgrade_bar"
UPGRADE_BUTTON = "upgrade_button"


@dataclass(frozen=True)
class BarCapture:
    """One captured frame plus the progress-bar ROI extracted from it."""

    frame: np.ndarray
    roi: np.ndarray


class UpgradeScreen:
    """Deep module over the Raid upgrade surface."""

    WINDOW_TITLE = RAID_WINDOW_TITLE

    def __init__(
        self,
        window_interaction_service: WindowInteractionProtocol,
        cache_service: CacheProtocol,
        screenshot_service: ScreenshotProtocol,
    ):
        self._window = window_interaction_service
        self._cache = cache_service
        self._screenshot = screenshot_service

        if not self._window.window_exists(self.WINDOW_TITLE):
            raise WindowNotFoundException(
                f"Raid window not found. Ensure {self.WINDOW_TITLE} is running."
            )

        size = self._window.get_window_size(self.WINDOW_TITLE)
        regions = self._cache.get_regions(size)
        if regions is None:
            raise WorkflowValidationError(
                f"No upgrade regions saved for this window size ({size}). "
                "Open the Calibration tab and select the upgrade regions first."
            )
        self._size = size
        self._bar_region = regions[UPGRADE_BAR]
        self._button_region = regions[UPGRADE_BUTTON]

    def start_attempt(self) -> None:
        """Begin an Attempt by clicking the upgrade-button Region."""
        self._guard_against_resize()
        self._window.click_region(self.WINDOW_TITLE, self._button_region)

    def cancel_attempt(self) -> None:
        """Abort the pending Attempt by clicking the same upgrade-button Region."""
        self._guard_against_resize()
        self._window.click_region(self.WINDOW_TITLE, self._button_region)

    def _guard_against_resize(self) -> None:
        """Raise if the window has been resized since Regions were resolved."""
        current_size = self._window.get_window_size(self.WINDOW_TITLE)
        if current_size != self._size:
            raise WindowResizedError(
                f"Raid window size changed from {self._size} to {current_size}. "
                "The saved regions no longer apply — re-calibrate for the new size."
            )

    def capture_progress_bar(self) -> BarCapture:
        """Take one screenshot and return the full frame plus the bar ROI."""
        frame = self._screenshot.take_screenshot(self.WINDOW_TITLE)
        roi = self._screenshot.extract_roi(frame, self._bar_region)
        return BarCapture(frame=frame, roi=roi)
