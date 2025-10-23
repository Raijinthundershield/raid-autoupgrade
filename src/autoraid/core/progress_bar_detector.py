"""Stateless detector for progress bar state from ROI images."""

from enum import Enum

import cv2
import numpy as np
from loguru import logger


class ProgressBarState(Enum):
    """Progress bar state detected from color analysis."""

    FAIL = "fail"
    PROGRESS = "progress"
    STANDBY = "standby"
    CONNECTION_ERROR = "connection_error"
    UNKNOWN = "unknown"


class ProgressBarStateDetector:
    """
    Detector for progress bar state from progress bar images.
    """

    def detect_state(self, progress_bar_image: np.ndarray) -> ProgressBarState:
        self._validate_input(progress_bar_image)

        avg_color = cv2.mean(progress_bar_image)[:3]

        if self._is_fail(avg_color):
            state = ProgressBarState.FAIL
        elif self._is_standby(avg_color):
            state = ProgressBarState.STANDBY
        elif self._is_progress(avg_color):
            state = ProgressBarState.PROGRESS
        elif self._is_connection_error(avg_color):
            state = ProgressBarState.CONNECTION_ERROR
        else:
            logger.debug("Unknown progress bar state detected")
            state = ProgressBarState.UNKNOWN

        return state

    @staticmethod
    def _is_progress(bgr_color: tuple[int, int, int], tolerance: int = 30) -> bool:
        b, g, r = bgr_color
        return b < 70 and abs(r - g) < 50

    @staticmethod
    def _is_fail(bgr_color: tuple[int, int, int], tolerance: int = 30) -> bool:
        b, g, r = bgr_color
        return b < 70 and g < 90 and r > 130

    @staticmethod
    def _is_standby(bgr_color: tuple[int, int, int], tolerance: int = 30) -> bool:
        b, g, r = bgr_color
        return b < 30 and g < 60 and r < 70

    @staticmethod
    def _is_connection_error(
        bgr_color: tuple[int, int, int], tolerance: int = 30
    ) -> bool:
        b, g, r = bgr_color
        return b > g and b > r and b > 50

    def _validate_input(self, progress_bar_image: np.ndarray) -> None:
        if progress_bar_image is None:
            raise ValueError("roi_image cannot be None")

        if progress_bar_image.size == 0:
            raise ValueError("roi_image is empty (size=0)")

        if progress_bar_image.ndim != 3:
            raise ValueError(
                f"roi_image must be 3D array, got shape {progress_bar_image.shape}"
            )

        if progress_bar_image.shape[2] != 3:
            raise ValueError(
                f"roi_image must have 3 channels (BGR), got {progress_bar_image.shape[2]}"
            )
