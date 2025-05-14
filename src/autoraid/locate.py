import numpy as np
from pyscreeze import Box, ImageNotFoundException, locate


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
) -> tuple[int, int, int, int] | None:
    """Locate the progress bar in the screenshot."""

    try:
        region: Box = locate(template, screenshot, confidence=confidence)
    except ImageNotFoundException:
        raise MissingRegionException(region_name)

    # Convert from pyscreeze format (left, top, width, height) to same format as select_region_with_prompt
    left, top, width, height = region
    region = (int(left), int(top), int(width), int(height))

    return region
