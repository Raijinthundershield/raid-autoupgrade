import json
import cv2
from raid_autoupgrade.cli import get_progress_bar_state

annotations_progress_bar = json.load(
    open("test/images/annotations_progress_bar_state.json")
)


def test_get_progress_bar_state():
    for image_path, true_state in annotations_progress_bar.items():
        image = cv2.imread(f"test/images/{image_path}")
        avg_color = cv2.mean(image)[:3]
        state = get_progress_bar_state(image)
        assert state == true_state, f"image_path: {image_path}, avg_color: {avg_color}"
