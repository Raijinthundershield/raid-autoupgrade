import json
import cv2
from autoraid.autoupgrade.autoupgrade import get_progress_bar_state

annotations_progress_bar = json.load(
    open("test/images/progress_bar_state/annotations_progress_bar_state.json")
)


def test_get_progress_bar_state():
    """
    Only important to differentiate between fail vs progress or standby.
    """

    for image_path, true_state in annotations_progress_bar.items():
        image = cv2.imread(f"test/images/{image_path}")
        avg_color = cv2.mean(image)[:3]
        state = get_progress_bar_state(image)

        # Check if we categorize the fails correctly
        if state == "fail" or true_state == "fail":
            assert (
                state == true_state
            ), f"image_path: {image_path}, avg_color: {avg_color}"
