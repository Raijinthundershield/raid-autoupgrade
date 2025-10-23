"""Stateless detector for progress bar state from ROI images."""

import numpy as np
from loguru import logger

from autoraid.core import progress_bar
from autoraid.core.progress_bar import ProgressBarState


class ProgressBarStateDetector:
    """
    Stateless detector for progress bar state from ROI images.
    """

    def detect_state(self, roi_image: np.ndarray) -> ProgressBarState:
        """Detect progress bar state from ROI image.

        Args:
            roi_image: BGR numpy array of progress bar region (H x W x 3)
        """
        # Input validation
        if roi_image is None:
            raise ValueError("roi_image cannot be None")

        if roi_image.size == 0:
            raise ValueError("roi_image is empty (size=0)")

        if roi_image.ndim != 3:
            raise ValueError(f"roi_image must be 3D array, got shape {roi_image.shape}")

        if roi_image.shape[2] != 3:
            raise ValueError(
                f"roi_image must have 3 channels (BGR), got {roi_image.shape[2]}"
            )

        state_str = progress_bar.get_progress_bar_state(roi_image)

        try:
            state = ProgressBarState(state_str)
        except ValueError:
            logger.warning(f"Unexpected state string: {state_str}")
            state = ProgressBarState.UNKNOWN

        if state == ProgressBarState.UNKNOWN:
            logger.debug("Unknown progress bar state detected")

        return state
