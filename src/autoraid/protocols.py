"""Protocol definitions for dependency injection.

This module defines protocol interfaces for all infrastructure services used in
the AutoRaid application. Protocols enable type-safe dependency injection while
decoupling consumers from concrete implementations.

All protocols are marked @runtime_checkable to support isinstance() validation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from autoraid.detection.progress_bar_detector import ProgressBarState
    from autoraid.services.network import NetworkAdapter, NetworkState


@runtime_checkable
class ProgressBarDetectorProtocol(Protocol):
    """Protocol for progress bar state detection."""

    def detect_state(self, progress_bar_image: np.ndarray) -> ProgressBarState:
        """Detect the state of the progress bar from an image.

        Args:
            progress_bar_image: NumPy array representing the progress bar region

        Returns:
            ProgressBarState enum indicating detected state
        """
        ...


@runtime_checkable
class WindowInteractionProtocol(Protocol):
    """Protocol for window operations."""

    def window_exists(self, window_title: str) -> bool:
        """Check if a window with the given title exists.

        Args:
            window_title: Title of the window to check

        Returns:
            True if window exists, False otherwise
        """
        ...

    def get_window_size(self, window_title: str) -> tuple[int, int]:
        """Get the size of a window.

        Args:
            window_title: Title of the window

        Returns:
            Tuple of (width, height) in pixels
        """
        ...

    def click_region(
        self, window_title: str, region: tuple[int, int, int, int]
    ) -> None:
        """Click a region within a window.

        Args:
            window_title: Title of the window
            region: Tuple of (left, top, width, height) defining click region
        """
        ...

    def activate_window(self, window_title: str) -> None:
        """Activate (bring to foreground) a window.

        Args:
            window_title: Title of the window to activate
        """
        ...


@runtime_checkable
class NetworkManagerProtocol(Protocol):
    """Protocol for network adapter management."""

    def check_network_access(self, timeout: float = 5.0) -> NetworkState:
        """Check internet connectivity.

        Args:
            timeout: Timeout in seconds for connectivity check

        Returns:
            NetworkState enum indicating network status
        """
        ...

    def toggle_adapters(
        self,
        adapter_ids: list[str],
        target_state: NetworkState,
        wait: bool = False,
        timeout: float | None = None,
    ) -> bool:
        """Enable or disable network adapters.

        Args:
            adapter_ids: List of adapter IDs to toggle
            target_state: Target state (ENABLED or DISABLED)
            wait: Whether to wait for state change completion
            timeout: Maximum time to wait for state change

        Returns:
            True if operation succeeded, False otherwise
        """
        ...

    def get_adapters(self) -> list[NetworkAdapter]:
        """Get list of all network adapters.

        Returns:
            List of NetworkAdapter objects
        """
        ...

    def wait_for_network_state(
        self, target_state: NetworkState, timeout: float
    ) -> None:
        """Wait for network to reach target state.

        Args:
            target_state: Desired network state
            timeout: Maximum time to wait in seconds

        Raises:
            TimeoutError: If state not reached within timeout
        """
        ...


@runtime_checkable
class CacheProtocol(Protocol):
    """Protocol for region/screenshot caching operations."""

    def get_regions(self, window_size: tuple[int, int]) -> dict | None:
        """Get cached regions for a window size.

        Args:
            window_size: Tuple of (width, height) in pixels

        Returns:
            Dictionary of region names to region tuples, or None if not cached
        """
        ...

    def set_regions(self, window_size: tuple[int, int], regions: dict) -> None:
        """Cache regions for a window size.

        Args:
            window_size: Tuple of (width, height) in pixels
            regions: Dictionary of region names to region tuples
        """
        ...

    def get_screenshot(self, window_size: tuple[int, int]) -> np.ndarray | None:
        """Get cached screenshot for a window size.

        Args:
            window_size: Tuple of (width, height) in pixels

        Returns:
            NumPy array of screenshot, or None if not cached
        """
        ...

    def set_screenshot(
        self, window_size: tuple[int, int], screenshot: np.ndarray
    ) -> None:
        """Cache screenshot for a window size.

        Args:
            window_size: Tuple of (width, height) in pixels
            screenshot: NumPy array of screenshot to cache
        """
        ...


@runtime_checkable
class ScreenshotProtocol(Protocol):
    """Protocol for screenshot capture and ROI extraction."""

    def take_screenshot(self, window_title: str) -> np.ndarray:
        """Capture a screenshot of a window.

        Args:
            window_title: Title of the window to capture

        Returns:
            NumPy array representing the screenshot
        """
        ...

    def extract_roi(
        self, screenshot: np.ndarray, region: tuple[int, int, int, int]
    ) -> np.ndarray:
        """Extract a region of interest from a screenshot.

        Args:
            screenshot: NumPy array of the full screenshot
            region: Tuple of (left, top, width, height) defining ROI

        Returns:
            NumPy array of the extracted region
        """
        ...


@runtime_checkable
class LocateRegionProtocol(Protocol):
    """Protocol for UI region detection."""

    def get_regions(
        self,
        screenshot: np.ndarray,
        manual: bool = False,
        override_cache: bool = False,
    ) -> dict[str, tuple[int, int, int, int]]:
        """Detect or retrieve cached UI regions from screenshot.

        Args:
            screenshot: NumPy array of the window screenshot
            manual: If True, prompt user for manual region selection
            override_cache: If True, ignore cached regions and re-detect

        Returns:
            Dictionary mapping region names to (left, top, width, height) tuples
        """
        ...


@runtime_checkable
class AppDataProtocol(Protocol):
    """Protocol for application directory configuration."""

    @property
    def cache_dir(self) -> Path:
        """Path to the cache directory."""
        ...

    @property
    def debug_enabled(self) -> bool:
        """Whether debug mode is enabled."""
        ...

    @property
    def debug_dir(self) -> Path | None:
        """Path to the debug directory, or None if debug mode disabled."""
        ...

    def ensure_directories(self) -> None:
        """Create cache and debug directories if they don't exist."""
        ...

    def get_log_file_path(self) -> Path | None:
        """Get the path to the log file, or None if debug mode disabled.

        Returns:
            Path to log file, or None if debug mode is disabled
        """
        ...
