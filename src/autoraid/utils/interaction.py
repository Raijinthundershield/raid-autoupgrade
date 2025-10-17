import cv2
import numpy as np
import pygetwindow
import pyautogui
import time
from loguru import logger


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

    def mouse_callback_select_rectangle(event, x, y, flags, param):
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

    cv2.setMouseCallback("Select Region", mouse_callback_select_rectangle)
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
