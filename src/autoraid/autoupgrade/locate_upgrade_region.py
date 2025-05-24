from functools import partial
import importlib.resources

import cv2
import numpy as np

from autoraid.locate import MissingRegionException, locate_region

template_dir = importlib.resources.files("autoraid") / "autoupgrade" / "templates"

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
    region_reduction = 5
    return (
        x + region_reduction,
        y + region_reduction,
        w - 2 * region_reduction,
        h - 2 * region_reduction,
    )


def locate_instant_upgrade_tickbox(screenshot: np.ndarray) -> tuple[int, int, int, int]:
    raise MissingRegionException("instant_upgrade_tickbox")
