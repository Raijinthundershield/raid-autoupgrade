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

    def __init__(self, use_minimize_trick: bool = True) -> None:
        """Initialize WindowInteractionService with no dependencies."""
        logger.debug("Initializing")
        self._use_minimize_trick = use_minimize_trick

    def window_exists(self, window_title: str) -> bool:
        """Check if a window with the given title exists.

        Args:
            window_title: Title of the window to check for

        Returns:
            True if window exists, False otherwise

        Raises:
            ValueError: If window_title is empty
        """
        logger.debug(f'window_exists called with window_title="{window_title}"')

        if not window_title:
            raise ValueError("window_title cannot be empty")

        windows = pygetwindow.getAllWindows()

        if not windows:
            logger.warning("No active windows found!")
            return False

        for window in windows:
            if window.title == window_title:
                logger.debug(f'Window "{window_title}" found')
                return True

        logger.debug(f'Window "{window_title}" not found')
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
        logger.info("Clicking region")
        logger.debug(
            f'click_region called with window_title="{window_title}", region={region}'
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
            # Activate window using minimize trick for reliability
            self.activate_window(window_title)

            # Get fresh window reference for coordinates
            windows = pygetwindow.getWindowsWithTitle(window_title)
            if not windows:
                raise WindowNotFoundException(
                    f'Window "{window_title}" not found. '
                    f"Ensure the application is running."
                )

            window = windows[0]

            # Calculate center of region relative to window
            center_x = left + width // 2
            center_y = top + height // 2

            # Calculate absolute screen coordinates
            screen_x = window.left + center_x
            screen_y = window.top + center_y

            logger.info(f"Clicking at ({screen_x}, {screen_y})")

            pyautogui.click(screen_x, screen_y)
            time.sleep(0.05)

            logger.debug("click_region completed successfully")

        except IndexError:
            logger.error(f'Window "{window_title}" not found')
            raise WindowNotFoundException(
                f'Window "{window_title}" not found. Ensure the application is running.'
            )
        except Exception as e:
            logger.error(f"Failed to click region: {e}")
            raise

    def get_window_size(self, window_title: str) -> tuple[int, int]:
        """Get the size of the specified window.

        Args:
            window_title: Title of the window to get size for

        Returns:
            Tuple of (width, height) in pixels

        Raises:
            WindowNotFoundException: If window not found
            ValueError: If window_title is empty
        """
        logger.debug(f'get_window_size called with window_title="{window_title}"')

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
            size = (window.width, window.height)

            logger.debug(f"get_window_size returned size {size[0]}x{size[1]}")

            return size

        except IndexError:
            logger.error(f'Window "{window_title}" not found')
            raise WindowNotFoundException(
                f'Window "{window_title}" not found. Ensure the application is running.'
            )
        except Exception as e:
            logger.error(f"Failed to get window size: {e}")
            raise

    def activate_window(self, window_title: str) -> None:
        """Activate (bring to foreground) the specified window.

        Args:
            window_title: Title of the window to activate
            use_minimize_trick: If True, use minimize-restore-activate sequence to force
                activation. This is more reliable for bringing background windows to
                foreground, especially when the application is running as admin.
                If False, use simple activation. Default: True.

        Raises:
            WindowNotFoundException: If window not found
            ValueError: If window_title is empty
        """
        logger.debug(
            f'activate_window called with window_title="{window_title}", '
            f"use_minimize_trick={self._use_minimize_trick}"
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

            if self._use_minimize_trick:
                logger.debug("Using minimize trick for activation")
                window.minimize()
                window.restore()
                window.activate()
            else:
                logger.debug("Using simple activation")
                window.activate()

            time.sleep(0.05)  # Give window time to activate

            logger.debug(f'Window "{window_title}" activated successfully')

        except IndexError:
            logger.error(f'Window "{window_title}" not found')
            raise WindowNotFoundException(
                f'Window "{window_title}" not found. Ensure the application is running.'
            )
        except Exception as e:
            logger.error(f"Failed to activate window: {e}")
            raise
