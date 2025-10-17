import json
from pathlib import Path
import cv2
from autoraid.core.progress_bar import get_progress_bar_state

import pytest

# Load annotations once
IMAGE_DIR = Path(__file__).parent.parent.parent / Path(
    "fixtures/images/progress_bar_state"
)
ANNOTATION_PATH = IMAGE_DIR / "annotations_progress_bar_state.json"
with open(ANNOTATION_PATH) as f:
    ANNOTATIONS = json.load(f)


@pytest.mark.parametrize("image_name, true_state", ANNOTATIONS.items())
def test_get_progress_bar_state(image_name, true_state):
    """
    Only important to differentiate between fail vs progress or standby.
    """

    image_path = IMAGE_DIR / image_name

    assert image_path.exists(), f" test image_path: {image_path} does not exist"

    image = cv2.imread(image_path)

    avg_color = cv2.mean(image)[:3]
    state = get_progress_bar_state(image)

    # Check if we categorize the fails correctly
    if state == "fail" or true_state == "fail":
        assert (
            state == true_state
        ), f"detected state: {state}, image_path: {image_path}, avg_color: {avg_color}"
