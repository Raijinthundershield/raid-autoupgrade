from functools import partial
import importlib.resources

import cv2
import numpy as np
from pyscreeze import Box, ImageNotFoundException, locate

template_dir = importlib.resources.files("autoraid") / "detection" / "templates"


class MissingRegionException(Exception):
    """Exception raised when a required region cannot be found in the screenshot."""

    def __init__(self, region_name: str):
        self.region_name = region_name
        self.message = f"Could not find {region_name} region in the screenshot."
        super().__init__(self.message)


def locate_region(
    screenshot: np.ndarray,
    template: np.ndarray,
    confidence: float = 0.8,
    region_name: str = "",
) -> tuple[int, int, int, int]:
    """Locate a template region in the screenshot.

    Args:
        screenshot: Screenshot to search in
        template: Template image to find
        confidence: Confidence threshold (0-1)
        region_name: Name of region for error messages

    Returns:
        Tuple of (left, top, width, height)

    Raises:
        MissingRegionException: If region cannot be found
    """
    try:
        region: Box = locate(template, screenshot, confidence=confidence)
    except ImageNotFoundException:
        raise MissingRegionException(region_name)

    # Convert from pyscreeze format (left, top, width, height)
    left, top, width, height = region
    return (int(left), int(top), int(width), int(height))


upgrade_button_template = cv2.imread(template_dir / "upgrade_button.png")
progress_bar_template = cv2.imread(template_dir / "progress_bar.png")
artifact_icon_template = cv2.imread(template_dir / "artifact_icon.png")

# objects that appear within the upgrade screen
locate_upgrade_button = partial(
    locate_region,
    template=upgrade_button_template,
    confidence=0.8,
    region_name="upgrade_button",
)

locate_artifact_icon = partial(
    locate_region,
    template=artifact_icon_template,
    confidence=0.6,
    region_name="artifact_icon",
)


# TODO: instead of reducing area, alter the conditions of finding the progress bar states.
def locate_progress_bar(screenshot: np.ndarray) -> tuple[int, int, int, int]:
    regions = locate_region(
        screenshot=screenshot,
        template=progress_bar_template,
        confidence=0.7,
        region_name="progress_bar",
    )
    x, y, w, h = regions
    region_reduction_x = 0.02 * w
    region_reduction_y = 0.15 * h
    return (
        int(x + region_reduction_x),
        int(y + region_reduction_y),
        int(w - 2 * region_reduction_x),
        int(h - 2 * region_reduction_y),
    )


def locate_instant_upgrade_tickbox(screenshot: np.ndarray) -> tuple[int, int, int, int]:
    raise MissingRegionException("instant_upgrade_tickbox")
