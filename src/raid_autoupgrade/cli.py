from collections import deque
import json
from pathlib import Path
import pygetwindow
from loguru import logger
import sys
import cv2
import numpy as np
import time

from raid_autoupgrade.progress_bar import get_progress_bar_state
from raid_autoupgrade.interaction import (
    take_screenshot_of_window,
    window_exists,
    click_region_center,
    select_region_with_prompt,
)

# from raid_autoupgrade.utils import get_timestamp
from raid_autoupgrade.visualization import get_roi_from_screenshot

# TODO: add when needed
# NOTE: Make this configurable...
# pytesseract.pytesseract.tesseract_cmd = (
#     "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
# )

# TODO: Make into cli that takes in max_fails.
# TODO: cache screenshot and regions. check for window size.
# TODO: disable and enable internet.
# TODO: if cancelled by connection error -> n_fails-1 AND continue upgrade if level<12.
# TODO: sometimes detect an extra fail when waiting for connection error on succesful upgrade
# TODO: Not fast enough when cancelling. Will almost always get one extra upgrade.
# TODO: add detection of level and stars to look at statistics.


def count_upgrade_fails(
    window_title: str,
    upgrade_bar_region: tuple[int, int, int, int],
    upgrade_button_region: tuple[int, int, int, int],
    max_fails: int = 99,
    check_interval: float = 0.025,
) -> int:
    """Count the number of upgrade files by counting the number of times the
    upgrade bar changes color to red.

    Args:
        window_title (str): Title of the window to monitor
        upgrade_bar_region (tuple): Region coordinates (left, top, width, height) relative to the window
        upgrade_button_region (tuple): Region coordinates (left, top, width, height) relative to the window
        max_fails (int, optional): Maximum number of fails to count before stopping. Defaults to 99.
        check_interval (float, optional): Time between checks in seconds. Defaults to 0.2.

    Returns:
        int: Number of fails detected

    Note:
        The function will stop monitoring if:
        - The maximum number of fails is reached
        - The upgrade bar stays in 'standby' state for 5 consecutive checks
        - The upgrade bar stays in 'connection_error' state for 5 consecutive checks
        - The upgrade bar stays in 'unknown' state for 5 consecutive checks
        - The user presses 'q' to stop monitoring
    """
    n_fails = 0
    current_state = None
    last_state = None
    max_equal_states = 4
    last_n_states = deque(maxlen=max_equal_states)

    logger.info("Starting to monitor upgrade bar color changes...")
    logger.info("Press 'q' to stop monitoring")

    # Click the upgrade level to start monitoring
    logger.info("Clicking upgrade button")
    click_region_center(window_title, upgrade_button_region)

    # Count the number of fails until the max is reached or the piece has been
    # upgraded.
    while n_fails < max_fails:
        screenshot = take_screenshot_of_window(window_title)
        upgrade_bar = get_roi_from_screenshot(screenshot, upgrade_bar_region)

        current_state = get_progress_bar_state(upgrade_bar)
        # logger.info(f"Current state: {current_state}")

        if last_state != current_state and current_state == "fail":
            n_fails += 1
            logger.info(
                f"{last_state} -> {current_state} (Total: {n_fails}  Max: {max_fails})"
            )
            # cv2.imwrite(f"upgrade_bar_{current_state}_{get_timestamp()}.png", upgrade_bar)

        if n_fails == max_fails:
            logger.info("Max fails reached. Clicking cancel upgrade.")
            click_region_center(window_title, upgrade_button_region)

        last_n_states.append(current_state)
        last_state = last_n_states[-1]

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

        # When a connection error occurs we have completed an upgrade while
        # having internet turned off.
        if len(last_n_states) >= max_equal_states and np.all(
            np.array(last_n_states) == "connection_error"
        ):
            logger.info(f"connection error for the last {max_equal_states} checks")
            break

        if len(last_n_states) >= max_equal_states and np.all(
            np.array(last_n_states) == "unknown"
        ):
            logger.info(f"unknown state for the last {max_equal_states} checks")
            break

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
        # "icon": "Click and drag to select icon",
    }

    # TODO: make more proper cache
    region_path = Path("regions.json")
    window = pygetwindow.getWindowsWithTitle(window_title)[0]
    window_size = [window.height, window.width]
    select_new_regions = True

    if region_path.exists():
        with open(region_path) as f:
            region_data = json.load(f)

        if region_data["window_size"] == window_size:
            regions = region_data["regions"]
            select_new_regions = False
            logger.info("Using cached regions")
        else:
            logger.info("Window size has changed. delete cached regions.")
            region_path.unlink()

    if select_new_regions:
        logger.info("Selecting new regions")

        # TODO: consider using pyautogui.locateOnScreen('calc7key.png')
        for name, prompt in region_prompts.items():
            region = select_region_with_prompt(screenshot, prompt)
            regions[name] = region
        region_data = {"window_size": window_size, "regions": regions}
        with open(region_path, "w") as f:
            json.dump(region_data, f)

    # logger.info("Showing selected regions")
    # show_regions(screenshot, regions)

    # 1. Count number of upgrades on one piece of equipment
    # 2. User selects new piece
    # 3. Upgrade until original count is reached

    # pyautogui.confirm(
    #     "Go to piece that you want to upgrade. Then press enter to continue."
    # )

    # Count upgrades until levelup or fails have been reaced
    n_fails = count_upgrade_fails(
        window_title, regions["upgrade_bar"], regions["upgrade_button"]
    )
    logger.info(f"Detected {n_fails} fails")


if __name__ == "__main__":
    main()
