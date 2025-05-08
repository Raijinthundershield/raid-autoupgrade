from collections import deque
import pygetwindow
from loguru import logger
import sys
import pyautogui
import cv2
import numpy as np
import time
import pytesseract
from datetime import datetime
from raid_autoupgrade.visualization import show_regions

# NOTE: Make this configurable...
pytesseract.pytesseract.tesseract_cmd = (
    "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
)


def get_timestamp() -> str:
    """Get current timestamp in a format suitable for filenames.

    Returns:
        str: Timestamp string in format YYYYMMDD_HHMMSS
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


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


def read_text_from_image(
    image: np.ndarray, region: tuple[int, int, int, int]
) -> tuple[str, np.ndarray, np.ndarray]:
    """Read text from a region in the image using OCR.

    Args:
        image (np.ndarray): The image to read from

    Returns:
        tuple: (text, original_roi, processed_roi) where:
            - text (str): The text read from the region
            - processed_image (np.ndarray): The processed region used for OCR
    """

    # Preprocess image for better OCR
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Apply thresholding to get black and white image
    _, image_processed = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # Perform OCR
    text = pytesseract.image_to_string(
        image_processed, config="--psm 7"
    )  # psm 7 for single line

    # TODO: REMOVE AFTER TESTING
    # # Save images with timestamp and change count
    # timestamp = get_timestamp()
    # cv2.imwrite(f"roi_{timestamp}_ {text}.png", image)
    # cv2.imwrite(f"roi_gray_{timestamp}_ {text}.png", gray)
    # cv2.imwrite(f"roi_processed_{timestamp}_{text}.png", image_processed)
    return text.strip(), image_processed


def get_progress_bar_state(progress_bar_roi: np.ndarray) -> str:
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
    return b < 70 and g < 100 and r > 90


def is_standby(bgr_color: tuple[int, int, int], tolerance: int = 30) -> bool:
    """Check if a BGR color is black within a tolerance.

    Args:
        bgr_color (tuple): BGR color values
        tolerance (int): Color matching tolerance

    Returns:
        bool: True if color is black, False otherwise
    """
    b, g, r = bgr_color
    return b < 60 and g < 60 and r < 70


def is_connection_error(bgr_color: tuple[int, int, int], tolerance: int = 30) -> bool:
    """Check if a BGR color is black within a tolerance.

    Args:
        bgr_color (tuple): BGR color values
        tolerance (int): Color matching tolerance

    Returns:
        bool: True if color is black, False otherwise
    """
    b, g, r = bgr_color
    return b > g and b > r and b > 50


def get_roi_from_screenshot(
    screenshot: np.ndarray, region: tuple[int, int, int, int]
) -> np.ndarray:
    """Extract a region of interest (ROI) from a screenshot.

    Args:
        screenshot (np.ndarray): The full screenshot image
        region (tuple): Region coordinates (left, top, width, height)

    Returns:
        np.ndarray: The extracted region of interest
    """
    left, top, width, height = region
    return screenshot[top : top + height, left : left + width]


def click_region_center(window_title: str, region: tuple[int, int, int, int]) -> None:
    """Click in the center of a region relative to the window.

    Args:
        window_title (str): Title of the window to click in
        region (tuple): Region coordinates (left, top, width, height)
    """
    try:
        # Get fresh window reference
        window = pygetwindow.getWindowsWithTitle(window_title)[0]
        window.activate()
        time.sleep(0.5)  # Give window time to activate

        # Calculate center of region relative to window
        left, top, width, height = region
        center_x = left + width // 2
        center_y = top + height // 2

        # Calculate absolute screen coordinates
        screen_x = window.left + center_x
        screen_y = window.top + center_y

        logger.debug(
            f"Clicking at {screen_x}, {screen_y}, center_coords: {center_x}, {center_y}"
        )
        logger.debug(
            f"Window coords: {window.left}, {window.top}, window_size: {window.width}, {window.height}"
        )

        # Click
        pyautogui.click(screen_x, screen_y)
    except IndexError:
        logger.error(f"Window '{window_title}' not found")
        raise
    except Exception as e:
        logger.error(f"Failed to click region: {str(e)}")
        raise


def count_upgrade_fails(
    window_title: str,
    upgrade_bar_region: tuple[int, int, int, int],
    upgrade_button_region: tuple[int, int, int, int],
    max_fails: int = 99,
    check_interval: float = 0.2,
) -> int:
    """Count the number of times the upgrade bar changes color between yellow and red.
    Ignores the initial change from black to yellow.

    Args:
        window_title (str): Title of the window to monitor
        upgrade_bar_region (tuple): Region coordinates (left, top, width, height)
        max_changes (int): Maximum number of changes to count
        check_interval (float): Time between checks in seconds

    Returns:
        int: Number of fails detected
    """
    n_fails = 0
    current_state = None
    last_state = None
    max_equal_states = 5
    last_n_states = deque(maxlen=max_equal_states)

    logger.info("Starting to monitor upgrade bar color changes...")
    logger.info("Press 'q' to stop monitoring")

    # Click the upgrade level to start monitoring
    click_region_center(window_title, upgrade_button_region)

    # Count the number of fails until the max is reached or the piece has been
    # upgraded.
    while n_fails <= max_fails:
        screenshot = take_screenshot_of_window(window_title)
        upgrade_bar = get_roi_from_screenshot(screenshot, upgrade_bar_region)

        current_state = get_progress_bar_state(upgrade_bar)
        logger.info(f"Current state: {current_state}")

        if last_state != current_state and current_state == "fail":
            n_fails += 1
            logger.info(f"{last_state} -> {current_state} (Total: {n_fails})")

        if current_state == "unknown":
            cv2.imwrite(f"unknown_{get_timestamp()}.png", upgrade_bar)

        last_n_states.append(current_state)
        last_state = last_n_states[-1]
        print(last_n_states)

        # Check for 'q' key press
        if cv2.waitKey(1) & 0xFF == ord("q"):
            logger.info("Monitoring stopped by user")
            break

        # If the ugrade has been completed, there will only be a black bar.
        if len(last_n_states) >= max_equal_states and np.all(
            np.array(last_n_states) == "standby"
        ):
            logger.info(f"Standby for the last {max_equal_states} checks")
            break

        if len(last_n_states) >= max_equal_states and np.all(
            np.array(last_n_states) == "connection_error"
        ):
            logger.info(f"connection error for the last {max_equal_states} checks")
            break

        # TODO: When the upgrade fails on connection error the bar region will look different.

        time.sleep(check_interval)

    logger.info(f"Finished monitoring. Detected {n_fails} fails.")
    return n_fails


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

    # Select regions
    for name, prompt in region_prompts.items():
        region = select_region_with_prompt(screenshot, prompt)
        regions[name] = region

        # TODO: make user confirm after each region is selected

    logger.info("Showing selected regions")
    show_regions(screenshot, regions)

    # 1. Count number of upgrades on one piece of equipment
    # 2. User selects new piece
    # 3. Upgrade until original count is reached

    input("Go to piece that you want to upgrade. Then press enter to continue.")

    # Click the upgrade button
    logger.info("Clicking upgrade button")
    click_region_center(window_title, regions["upgrade_button"])
    time.sleep(0.5)  # Give time for click to register

    # Count upgrades until levelup or fails have been reaced
    max_fails = count_upgrade_fails(
        window_title, regions["upgrade_bar"], regions["upgrade_button"], max_fails=50
    )
    logger.info(f"Detected {max_fails} fails")

    # input(
    #     "Go to piece that you want to spend upgrades on. Then press enter to continue."
    # )
    # while True:
    #     screenshot = take_screenshot_of_window(window_title)
    #     roi = get_roi_from_screenshot(screenshot, regions["upgrade_button"])

    #     # TODO: need to check that the level is read in correctly
    #     # level_before = read_text_from_image(roi, regions["upgrade_level"])

    #     fails = count_upgrade_fails(
    #         window_title, regions["upgrade_bar"], max_fails=max_fails
    #     )

    #     screenshot = take_screenshot_of_window(window_title)
    #     level_after = read_text_from_image(screenshot, regions["upgrade_button"])

    #     # TODO: check if we have reached the count of upgrades
    #     #   - a. if we have more to count, continue
    #     #   - b. if we have reached the count, stop and prompt user to upgrade the original piece

    # logger.info(f"Detected {fails} upgrade levels")


if __name__ == "__main__":
    main()
