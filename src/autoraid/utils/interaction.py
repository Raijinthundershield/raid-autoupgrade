import time

import pyautogui
import pygetwindow
from loguru import logger


def click_region_center(window_title: str, region: tuple[int, int, int, int]) -> None:
    """Click in the center of a region relative to the window.

    Args:
        window_title (str): Title of the window to click in
        region (tuple): Region coordinates (left, top, width, height) relative to the window
    """
    try:
        # Get fresh window reference
        window = pygetwindow.getWindowsWithTitle(window_title)[0]
        window.activate()
        time.sleep(0.05)  # Give window time to activate

        # Calculate center of region relative to window
        left, top, width, height = region
        center_x = left + width // 2
        center_y = top + height // 2

        # Calculate absolute screen coordinates
        screen_x = window.left + center_x
        screen_y = window.top + center_y

        logger.info(f"Click {screen_x}, {screen_y}")

        pyautogui.click(screen_x, screen_y)
        time.sleep(0.05)

    except IndexError:
        logger.error(f"Window '{window_title}' not found")
        raise
    except Exception as e:
        logger.error(f"Failed to click region: {str(e)}")
        raise
