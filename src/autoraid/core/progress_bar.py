from enum import Enum

import cv2
import numpy as np


class ProgressBarState(Enum):
    """Progress bar state detected from color analysis."""

    FAIL = "fail"
    PROGRESS = "progress"
    STANDBY = "standby"
    CONNECTION_ERROR = "connection_error"
    UNKNOWN = "unknown"


def get_progress_bar_state(progress_bar_roi: np.ndarray) -> str:
    """Get the state of the progress bar based on its color.

    Args:
        progress_bar_roi (np.ndarray): Region of interest containing the progress bar

    Returns:
        str: State of the progress bar ('fail', 'standby', 'progress', 'connection_error', or 'unknown')
    """
    avg_color = cv2.mean(progress_bar_roi)[:3]

    if is_fail(avg_color):
        return "fail"
    elif is_standby(avg_color):
        return "standby"
    elif is_progress(avg_color):
        return "progress"
    elif is_connection_error(avg_color):
        return "connection_error"
    else:
        return "unknown"


def is_progress(bgr_color: tuple[int, int, int], tolerance: int = 30) -> bool:
    """Check if a BGR color is yellow within a tolerance.

    Args:
        bgr_color (tuple): BGR color values
        tolerance (int): Color matching tolerance

    Returns:
        bool: True if color is yellow, False otherwise
    """
    b, g, r = bgr_color
    return b < 70 and abs(r - g) < 50


def is_fail(bgr_color: tuple[int, int, int], tolerance: int = 30) -> bool:
    """Check if a BGR color is red within a tolerance.

    Args:
        bgr_color (tuple): BGR color values
        tolerance (int): Color matching tolerance

    Returns:
        bool: True if color is red, False otherwise
    """
    b, g, r = bgr_color
    return b < 70 and g < 90 and r > 130


def is_standby(bgr_color: tuple[int, int, int], tolerance: int = 30) -> bool:
    """Check if a BGR color is black within a tolerance.

    Args:
        bgr_color (tuple): BGR color values
        tolerance (int): Color matching tolerance

    Returns:
        bool: True if color is black, False otherwise
    """
    b, g, r = bgr_color
    return b < 30 and g < 60 and r < 70


def is_connection_error(bgr_color: tuple[int, int, int], tolerance: int = 30) -> bool:
    """Check if a BGR color indicates a connection error.

    Args:
        bgr_color (tuple): BGR color values
        tolerance (int): Color matching tolerance

    Returns:
        bool: True if color indicates connection error, False otherwise
    """
    b, g, r = bgr_color
    return b > g and b > r and b > 50
