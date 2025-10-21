"""Screenshot service for capturing window screenshots and extracting ROIs.

This service handles all screenshot operations including:
- Taking screenshots of windows
- Extracting regions of interest from screenshots
"""

import cv2
import numpy as np
import pyautogui
import pygetwindow
from loguru import logger

from autoraid.exceptions import WindowNotFoundException
from autoraid.services.window_interaction_service import WindowInteractionService


class ScreenshotService:
    """Service for screenshot operations.

    Responsibilities:
    - Capture window screenshots
    - Extract regions of interest from screenshots
    """

    def __init__(self, window_interaction_service: WindowInteractionService) -> None:
        """Initialize ScreenshotService with window interaction service dependency.

        Args:
            window_interaction_service: Service for window activation and interaction
        """
        logger.debug("Initializing")
        self._window_interaction_service = window_interaction_service

    def take_screenshot(self, window_title: str) -> np.ndarray:
        """Take a screenshot of the specified window.

        Args:
            window_title: Title of the window to capture

        Returns:
            BGR image of the window as numpy array

        Raises:
            WindowNotFoundException: If window not found
            ValueError: If window_title is empty
        """
        logger.debug(f'take_screenshot called with window_title="{window_title}"')

        if not window_title:
            raise ValueError("window_title cannot be empty")

        try:
            self._window_interaction_service.activate_window(window_title)

            # Get window reference for coordinates
            windows = pygetwindow.getWindowsWithTitle(window_title)
            if not windows:
                raise WindowNotFoundException(
                    f'Window "{window_title}" not found. '
                    f"Ensure the application is running."
                )

            window = windows[0]

            # Capture screenshot of window region
            screenshot = pyautogui.screenshot(
                region=(window.left, window.top, window.width, window.height)
            )
            screenshot = np.array(screenshot)
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)

            logger.debug(
                f"take_screenshot returned screenshot of size {screenshot.shape[1]}x{screenshot.shape[0]}"
            )
            return screenshot

        except IndexError:
            logger.error(f'Window "{window_title}" not found')
            raise WindowNotFoundException(
                f'Window "{window_title}" not found. Ensure the application is running.'
            )
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            raise

    def extract_roi(
        self, screenshot: np.ndarray, region: tuple[int, int, int, int]
    ) -> np.ndarray:
        """Extract region of interest from screenshot.

        Args:
            screenshot: Full window screenshot as numpy array
            region: Region coordinates (left, top, width, height)

        Returns:
            Extracted ROI as numpy array

        Raises:
            ValueError: If region coordinates are invalid
        """
        logger.debug(f"extract_roi called with region={region}")

        left, top, width, height = region

        # Validate region coordinates
        if left < 0 or top < 0:
            raise ValueError(
                f"Invalid region coordinates: left={left}, top={top}. "
                f"Coordinates must be non-negative."
            )

        if width <= 0 or height <= 0:
            raise ValueError(
                f"Invalid region dimensions: width={width}, height={height}. "
                f"Dimensions must be positive."
            )

        # Validate region is within screenshot bounds
        screenshot_height, screenshot_width = screenshot.shape[:2]
        if left + width > screenshot_width or top + height > screenshot_height:
            raise ValueError(
                f"Region ({left}, {top}, {width}, {height}) exceeds "
                f"screenshot bounds ({screenshot_width}x{screenshot_height})"
            )

        # Extract ROI
        roi = screenshot[top : top + height, left : left + width]

        logger.debug(f"extract_roi returned ROI of size {roi.shape[1]}x{roi.shape[0]}")
        return roi
