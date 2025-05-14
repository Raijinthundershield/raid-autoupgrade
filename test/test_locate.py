import json
import cv2
from pathlib import Path

import numpy as np
import pytest

from autoraid.autoupgrade.locate_upgrade_region import (
    locate_progress_bar,
    locate_upgrade_button,
    upgrade_button_template,
    progress_bar_template,
)


# Load annotations once
image_dir = Path(__file__).parent / Path("images/locate_upgrade_regions")
annotation_path = image_dir / "annotation.json"
with open(annotation_path) as f:
    annotations = json.load(f)
annotations


@pytest.fixture()
def image_dir():
    return Path(__file__).parent / Path("images/locate_upgrade_regions")


@pytest.mark.parametrize("template", [upgrade_button_template, progress_bar_template])
def test_upgrade_templates(template: np.ndarray):
    """Test the upgrade templates set up correctly wrt. adding data to the package."""

    assert isinstance(template, np.ndarray)


@pytest.mark.parametrize(
    "annotation_id, annotation",
    list(annotations.items()),
)
def test_locate_upgrade_button(annotation_id, annotation, image_dir):
    screenshot_path = image_dir / annotation["screenshot"]
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
    list(annotations.items()),
)
def test_locate_progress_bar(annotation_id, annotation, image_dir):
    screenshot_path = image_dir / annotation["screenshot"]
    screenshot = cv2.imread(str(screenshot_path))
    progress_bar_region = annotation["progress_bar_region"]

    detected_region: tuple[int, int, int, int] = locate_progress_bar(screenshot)

    tolerance = 10
    is_within_tolerance = (
        abs(detected_region[0] - progress_bar_region[0]) <= tolerance
        and abs(detected_region[1] - progress_bar_region[1]) <= tolerance
        and abs(detected_region[2] - progress_bar_region[2]) <= tolerance
        and abs(detected_region[3] - progress_bar_region[3]) <= tolerance
    )

    assert is_within_tolerance, (
        f"Progress bar region mismatch for {annotation_id}\n"
        f"Expected: {progress_bar_region}\n"
        f"Got: ({detected_region[0]}, {detected_region[1]}, "
        f"{detected_region[2]}, {detected_region[3]})"
    )
