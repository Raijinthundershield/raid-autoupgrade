import pygetwindow
from loguru import logger
import sys
import pyautogui
import cv2
import numpy as np
import time
from raid_autoupgrade.visualization import show_regions


def take_screenshot_of_window(window_title: str) -> np.ndarray:
    """Take a screenshot of the specified window.

    Args:
        window_title (str): Title of the window to capture

    Returns:
        np.ndarray: BGR image of the window
    """
    window = pygetwindow.getWindowsWithTitle(window_title)[0]
    window.activate()
    time.sleep(0.5)

    screenshot = pyautogui.screenshot(
        region=(window.left, window.top, window.width, window.height)
    )
    screenshot = np.array(screenshot)
    screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)

    return screenshot


def select_region_from_image(image: np.ndarray) -> tuple[int, int, int, int] | None:
    """Let user select a region by clicking and dragging on an image.

    Args:
        image (np.ndarray): The image to select region from

    Returns:
        tuple: (left, top, width, height) where:
            - left (int): X coordinate of the top-left corner of the selected region
            - top (int): Y coordinate of the top-left corner of the selected region
            - width (int): Width of the selected region
            - height (int): Height of the selected region
    """
    # Create window for selection
    cv2.namedWindow("Select Region", cv2.WINDOW_NORMAL)
    cv2.imshow("Select Region", image)

    # Variables for selection
    start_point = None
    end_point = None
    selecting = False

    def mouse_callback(event, x, y, flags, param):
        nonlocal start_point, end_point, selecting, image

        if event == cv2.EVENT_LBUTTONDOWN:
            start_point = (x, y)
            selecting = True

        elif event == cv2.EVENT_MOUSEMOVE and selecting:
            temp_frame = image.copy()
            cv2.rectangle(temp_frame, start_point, (x, y), (0, 255, 0), 2)
            cv2.imshow("Select Region", temp_frame)

        elif event == cv2.EVENT_LBUTTONUP:
            end_point = (x, y)
            selecting = False
            cv2.destroyAllWindows()

    cv2.setMouseCallback("Select Region", mouse_callback)
    cv2.waitKey(0)

    if start_point and end_point:
        # Calculate region coordinates relative to window
        left = min(start_point[0], end_point[0])
        top = min(start_point[1], end_point[1])
        width = abs(end_point[0] - start_point[0])
        height = abs(end_point[1] - start_point[1])
        return (left, top, width, height)

    else:
        logger.warning("No region selected")
        return None


def window_exists(window_title: str):
    """Check if a window with the given title exists.

    Args:
        window_title (str): The title of the window to check for

    Returns:
        bool: True if window exists, False otherwise
    """
    windows = pygetwindow.getAllWindows()

    if not windows:
        logger.warning("No active windows found!")

    for window in pygetwindow.getAllWindows():
        if window.title == window_title:
            return True
    else:
        return False


def select_region_with_prompt(
    image: np.ndarray, prompt: str
) -> tuple[int, int, int, int]:
    """Select a region from a window with a user prompt.

    Args:
        window_title (str): Title of the window to select from
        prompt (str): Message to show to the user

    Returns:
        tuple: (screenshot, region) where:
            - screenshot (np.ndarray): The captured window image
            - region (tuple): Selected region coordinates (left, top, width, height)
    """
    logger.info(prompt)
    region = select_region_from_image(image)
    logger.info(f"Region selected: {region}")
    return region


def main():
    # Check if we can find the Raid window
    window_title = "Raid: Shadow Legends"
    if not window_exists(window_title):
        logger.warning("Raid window not found. Check if Raid is running.")
        sys.exit(1)
    screenshot = take_screenshot_of_window(window_title)

    # Select regions
    regions = {}
    region_prompts = {
        "upgrade_bar": "Click and drag to select upgrade bar",
        "upgrade_button": "Click and drag to select upgrade button",
        "icon": "Click and drag to select icon",
    }

    # Select remaining regions
    for name, prompt in region_prompts.items():
        # NOTE: assumes the window does not change
        region = select_region_with_prompt(screenshot, prompt)
        regions[name] = region

        # TODO: make user confirm after each region is selected

    if regions:
        logger.info("Showing selected regions")
        show_regions(screenshot, regions)

    else:
        logger.warning("No region selected")

    logger.info("Waiting for user to close window")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
