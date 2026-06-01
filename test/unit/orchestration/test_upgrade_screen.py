"""Unit tests for the UpgradeScreen deep module.

UpgradeScreen is exercised in full isolation: fake window-interaction, cache, and
screenshot services are injected, and assertions are on exception type and side
effects (which Region was clicked, how many screenshots were taken) rather than on
error-message wording.
"""

from __future__ import annotations

import numpy as np
import pytest

from raid_autoupgrade.constants import RAID_WINDOW_TITLE
from raid_autoupgrade.exceptions import (
    WindowNotFoundException,
    WindowResizedError,
    WorkflowValidationError,
)

UPGRADE_BAR_REGION = (10, 20, 100, 30)
UPGRADE_BUTTON_REGION = (40, 200, 80, 40)
DEFAULT_SIZE = (800, 600)


def _regions() -> dict:
    return {
        "upgrade_bar": UPGRADE_BAR_REGION,
        "upgrade_button": UPGRADE_BUTTON_REGION,
    }


class FakeWindow:
    """Records clicks; window size is mutable to simulate a mid-run resize."""

    def __init__(self, *, exists: bool = True, size: tuple[int, int] = DEFAULT_SIZE):
        self._exists = exists
        self.size = size
        self.clicks: list[tuple[str, tuple[int, int, int, int]]] = []

    def window_exists(self, window_title: str) -> bool:
        return self._exists

    def get_window_size(self, window_title: str) -> tuple[int, int]:
        return self.size

    def click_region(
        self, window_title: str, region: tuple[int, int, int, int]
    ) -> None:
        self.clicks.append((window_title, region))

    def activate_window(self, window_title: str) -> None:
        pass


class FakeCache:
    """Returns regions keyed by size; records every lookup."""

    def __init__(self, regions_by_size: dict[tuple[int, int], dict] | None = None):
        if regions_by_size is None:
            regions_by_size = {DEFAULT_SIZE: _regions()}
        self._regions_by_size = regions_by_size
        self.get_regions_calls: list[tuple[int, int]] = []

    def get_regions(self, window_size: tuple[int, int]) -> dict | None:
        self.get_regions_calls.append(window_size)
        return self._regions_by_size.get(window_size)


class FakeScreenshot:
    """Hands back a sentinel frame and a per-region sentinel ROI; counts captures."""

    def __init__(self):
        self.frame = np.zeros((600, 800, 3), dtype=np.uint8)
        self.screenshots_taken = 0
        self.extract_calls: list[tuple[int, int, int, int]] = []

    def take_screenshot(self, window_title: str) -> np.ndarray:
        self.screenshots_taken += 1
        return self.frame

    def extract_roi(
        self, screenshot: np.ndarray, region: tuple[int, int, int, int]
    ) -> np.ndarray:
        self.extract_calls.append(region)
        # Distinct sentinel so the ROI can be told apart from the full frame.
        return np.ones((region[3], region[2], 3), dtype=np.uint8)


def _make_screen():
    from raid_autoupgrade.orchestration.upgrade_screen import UpgradeScreen

    window = FakeWindow()
    cache = FakeCache()
    screenshot = FakeScreenshot()
    screen = UpgradeScreen(
        window_interaction_service=window,
        cache_service=cache,
        screenshot_service=screenshot,
    )
    return screen, window, cache, screenshot


class TestUpgradeScreen:
    def test_start_attempt_clicks_the_upgrade_button_region(self):
        screen, window, _cache, _screenshot = _make_screen()

        screen.start_attempt()

        assert window.clicks == [(RAID_WINDOW_TITLE, UPGRADE_BUTTON_REGION)]

    def test_start_attempt_raises_when_window_resized(self):
        screen, window, _cache, _screenshot = _make_screen()

        # Window drifts to a new size after construction.
        window.size = (1024, 768)

        with pytest.raises(WindowResizedError):
            screen.start_attempt()

        # Loud failure: no click lands on the now-stale Region.
        assert window.clicks == []

    def test_cancel_attempt_raises_when_window_resized(self):
        screen, window, _cache, _screenshot = _make_screen()

        window.size = (1024, 768)

        with pytest.raises(WindowResizedError):
            screen.cancel_attempt()

        assert window.clicks == []

    def test_capture_progress_bar_does_not_guard_against_resize(self):
        # The guard is on the click actions only; per-frame capture keeps reading
        # so a mid-loop resize is caught at the next attempt boundary, not per frame.
        screen, window, _cache, screenshot = _make_screen()

        window.size = (1024, 768)

        capture = screen.capture_progress_bar()

        assert screenshot.screenshots_taken == 1
        assert capture.frame is screenshot.frame

    def test_capture_progress_bar_returns_full_frame_and_bar_roi(self):
        screen, _window, _cache, screenshot = _make_screen()

        capture = screen.capture_progress_bar()

        # One screenshot per capture; the ROI is extracted from the bar Region.
        assert screenshot.screenshots_taken == 1
        assert capture.frame is screenshot.frame
        assert screenshot.extract_calls == [UPGRADE_BAR_REGION]
        # ROI is the bar Region cut-out, distinct from the full frame.
        assert capture.roi.shape == (
            UPGRADE_BAR_REGION[3],
            UPGRADE_BAR_REGION[2],
            3,
        )

    def test_upgrade_screen_satisfies_protocol(self):
        from raid_autoupgrade.protocols import UpgradeScreenProtocol

        screen, _window, _cache, _screenshot = _make_screen()

        assert isinstance(screen, UpgradeScreenProtocol)

    def test_regions_resolved_once_at_construction(self):
        screen, _window, cache, _screenshot = _make_screen()

        # Construction did the single lookup.
        assert cache.get_regions_calls == [DEFAULT_SIZE]

        # Subsequent actions reuse the resolved Regions — no further cache hits.
        screen.start_attempt()
        screen.capture_progress_bar()
        screen.cancel_attempt()

        assert cache.get_regions_calls == [DEFAULT_SIZE]

    def test_construction_raises_when_window_missing(self):
        from raid_autoupgrade.orchestration.upgrade_screen import UpgradeScreen

        window = FakeWindow(exists=False)

        with pytest.raises(WindowNotFoundException):
            UpgradeScreen(
                window_interaction_service=window,
                cache_service=FakeCache(),
                screenshot_service=FakeScreenshot(),
            )

    def test_cancel_attempt_clicks_the_upgrade_button_region(self):
        screen, window, _cache, _screenshot = _make_screen()

        screen.cancel_attempt()

        assert window.clicks == [(RAID_WINDOW_TITLE, UPGRADE_BUTTON_REGION)]

    def test_construction_raises_when_no_regions_for_current_size(self):
        from raid_autoupgrade.orchestration.upgrade_screen import UpgradeScreen

        # Window present, but the cache has nothing for its current size.
        window = FakeWindow(size=(1024, 768))
        cache = FakeCache(regions_by_size={DEFAULT_SIZE: _regions()})

        with pytest.raises(WorkflowValidationError):
            UpgradeScreen(
                window_interaction_service=window,
                cache_service=cache,
                screenshot_service=FakeScreenshot(),
            )
