import json
import cv2
from pathlib import Path

import numpy as np
import pytest

from autoraid.detection.locate_region import (
    locate_progress_bar,
    locate_upgrade_button,
    upgrade_button_template,
    progress_bar_template,
)


# Load annotations once
IMAGE_DIR = Path(__file__).parent.parent / Path(
    "fixtures/images/locate_upgrade_regions"
)
ANNOTATION_PATH = IMAGE_DIR / "annotation.json"
with open(ANNOTATION_PATH) as f:
    ANNOTATIONS = json.load(f)


@pytest.fixture()
def image_dir():
    return Path(__file__).parent.parent / Path("fixtures/images/locate_upgrade_regions")


@pytest.mark.parametrize("template", [upgrade_button_template, progress_bar_template])
def test_upgrade_templates(template: np.ndarray):
    """Test the upgrade templates set up correctly wrt. adding data to the package."""

    assert isinstance(template, np.ndarray)


@pytest.mark.parametrize(
    "annotation_id, annotation",
    list(ANNOTATIONS.items()),
)
def test_locate_upgrade_button(annotation_id, annotation):
    screenshot_path = IMAGE_DIR / annotation["screenshot"]
    screenshot = cv2.imread(str(screenshot_path))
    upgrade_button_region = annotation["upgrade_button_region"]

    detected_region: tuple[int, int, int, int] = locate_upgrade_button(screenshot)

    tolerance = 5
    is_within_tolerance = (
        abs(detected_region[0] - upgrade_button_region[0]) <= tolerance
        and abs(detected_region[1] - upgrade_button_region[1]) <= tolerance
        and abs(detected_region[2] - upgrade_button_region[2]) <= tolerance
        and abs(detected_region[3] - upgrade_button_region[3]) <= tolerance
    )

    assert is_within_tolerance, (
        f"Upgrade button region mismatch for {annotation_id}\n"
        f"Expected: {upgrade_button_region}\n"
        f"Got: ({detected_region[0]}, {detected_region[1]}, "
        f"{detected_region[2]}, {detected_region[3]})"
    )


@pytest.mark.parametrize(
    "annotation_id, annotation",
    list(ANNOTATIONS.items()),
)
def test_locate_progress_bar(annotation_id, annotation):
    screenshot_path = IMAGE_DIR / annotation["screenshot"]
    screenshot = cv2.imread(str(screenshot_path))
    progress_bar_region = annotation["progress_bar_region"]

    detected_region: tuple[int, int, int, int] = locate_progress_bar(screenshot)

    tolerance = 0.2
    is_within_tolerance = (
        abs(detected_region[0] - progress_bar_region[0])
        <= tolerance * progress_bar_region[0]
        and abs(detected_region[1] - progress_bar_region[1])
        <= tolerance * progress_bar_region[1]
        and abs(detected_region[2] - progress_bar_region[2])
        <= tolerance * progress_bar_region[2]
        and abs(detected_region[3] - progress_bar_region[3])
        <= tolerance * progress_bar_region[3]
    )

    assert is_within_tolerance, (
        f"Progress bar region mismatch for {annotation_id}\n"
        f"Expected: {progress_bar_region}\n"
        f"Got: ({detected_region[0]}, {detected_region[1]}, "
        f"{detected_region[2]}, {detected_region[3]})"
    )
