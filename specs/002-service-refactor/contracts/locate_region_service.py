"""Locate region service interface protocol."""

from typing import Protocol
import numpy as np


class LocateRegionServiceProtocol(Protocol):
    """Interface for region detection."""

    def get_regions(
        self, screenshot: np.ndarray, window_size: tuple[int, int], manual: bool = False
    ) -> dict:
        """Get upgrade UI regions (automatic or manual selection).

        Args:
            screenshot: Full window screenshot as numpy array
            window_size: Tuple of (width, height) in pixels
            manual: If True, force manual selection

        Returns:
            Dictionary of regions {name: (left, top, width, height)}
            Required keys: upgrade_bar, upgrade_button, artifact_icon

        Raises:
            RegionDetectionError: If all detection methods fail
        """
        ...
