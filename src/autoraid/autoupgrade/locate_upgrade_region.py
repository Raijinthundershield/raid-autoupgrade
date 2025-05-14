from functools import partial
import importlib.resources

import cv2

from autoraid.locate import locate_region

template_dir = importlib.resources.files("autoraid") / "autoupgrade" / "templates"

upgrade_button_template = cv2.imread(template_dir / "upgrade_button.png")
progress_bar_template = cv2.imread(template_dir / "progress_bar.png")

# objects that appear within the upgrade screen
locate_upgrade_button = partial(
    locate_region,
    template=upgrade_button_template,
    confidence=0.8,
    region_name="upgrade_button",
)

locate_progress_bar = partial(
    locate_region,
    template=progress_bar_template,
    confidence=0.65,
    region_name="progress_bar",
)
