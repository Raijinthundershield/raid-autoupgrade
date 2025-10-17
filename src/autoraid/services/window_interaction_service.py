"""Window interaction service for clicking and activating windows.

This service handles all window interaction operations including:
- Checking window existence
- Clicking regions within windows
- Activating windows
"""

import time

import pyautogui
import pygetwindow
from loguru import logger

from autoraid.exceptions import WindowNotFoundException


class WindowInteractionService:
    """Service for window interaction operations.

    Responsibilities:
    - Check window existence
    - Click regions within windows
    - Activate windows
    """

    def __init__(self) -> None:
        """Initialize WindowInteractionService with no dependencies."""
        logger.debug("[WindowInteractionService] Initializing")

    def window_exists(self, window_title: str) -> bool:
        """Check if a window with the given title exists.

        Args:
            window_title: Title of the window to check for

        Returns:
            True if window exists, False otherwise

        Raises:
            ValueError: If window_title is empty
        """
        logger.debug(
            f'[WindowInteractionService] window_exists called with window_title="{window_title}"'
        )

        if not window_title:
            raise ValueError("window_title cannot be empty")

        windows = pygetwindow.getAllWindows()

        if not windows:
            logger.warning("[WindowInteractionService] No active windows found!")
            return False

        for window in windows:
            if window.title == window_title:
                logger.debug(
                    f'[WindowInteractionService] Window "{window_title}" found'
                )
                return True

        logger.debug(f'[WindowInteractionService] Window "{window_title}" not found')
        return False

    def click_region(
        self, window_title: str, region: tuple[int, int, int, int]
    ) -> None:
        """Click in the center of a region relative to the window.

        Args:
            window_title: Title of the window to click in
            region: Region coordinates (left, top, width, height) relative to the window

        Raises:
            WindowNotFoundException: If window not found
            ValueError: If window_title is empty or region is invalid
        """
        logger.info("[WindowInteractionService] Clicking region")
        logger.debug(
            f'[WindowInteractionService] click_region called with window_title="{window_title}", region={region}'
        )

        if not window_title:
            raise ValueError("window_title cannot be empty")

        left, top, width, height = region

        # Validate region dimensions
        if width <= 0 or height <= 0:
            raise ValueError(
                f"Invalid region dimensions: width={width}, height={height}. "
                f"Dimensions must be positive."
            )

        try:
            # Get fresh window reference
            windows = pygetwindow.getWindowsWithTitle(window_title)
            if not windows:
                raise WindowNotFoundException(
                    f'Window "{window_title}" not found. '
                    f"Ensure the application is running."
                )

            window = windows[0]
            window.activate()
            time.sleep(0.05)  # Give window time to activate

            # Calculate center of region relative to window
            center_x = left + width // 2
            center_y = top + height // 2

            # Calculate absolute screen coordinates
            screen_x = window.left + center_x
            screen_y = window.top + center_y

            logger.info(
                f"[WindowInteractionService] Clicking at ({screen_x}, {screen_y})"
            )

            pyautogui.click(screen_x, screen_y)
            time.sleep(0.05)

            logger.debug(
                "[WindowInteractionService] click_region completed successfully"
            )

        except IndexError:
            logger.error(
                f'[WindowInteractionService] Window "{window_title}" not found'
            )
            raise WindowNotFoundException(
                f'Window "{window_title}" not found. Ensure the application is running.'
            )
        except Exception as e:
            logger.error(f"[WindowInteractionService] Failed to click region: {e}")
            raise

    def activate_window(self, window_title: str) -> None:
        """Activate (bring to foreground) the specified window.

        Args:
            window_title: Title of the window to activate

        Raises:
            WindowNotFoundException: If window not found
            ValueError: If window_title is empty
        """
        logger.debug(
            f'[WindowInteractionService] activate_window called with window_title="{window_title}"'
        )

        if not window_title:
            raise ValueError("window_title cannot be empty")

        try:
            windows = pygetwindow.getWindowsWithTitle(window_title)
            if not windows:
                raise WindowNotFoundException(
                    f'Window "{window_title}" not found. '
                    f"Ensure the application is running."
                )

            window = windows[0]
            window.activate()
            time.sleep(0.05)  # Give window time to activate

            logger.debug(
                f'[WindowInteractionService] Window "{window_title}" activated successfully'
            )

        except IndexError:
            logger.error(
                f'[WindowInteractionService] Window "{window_title}" not found'
            )
            raise WindowNotFoundException(
                f'Window "{window_title}" not found. Ensure the application is running.'
            )
        except Exception as e:
            logger.error(f"[WindowInteractionService] Failed to activate window: {e}")
            raise
