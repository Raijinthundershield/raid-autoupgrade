import cv2
from loguru import logger
import numpy as np


def add_region_to_image(
    image: np.ndarray,
    region: tuple[int, int, int, int],
    name: str = None,
    color: tuple[int, int, int] = (0, 255, 0),
) -> np.ndarray:
    """Visualize a single region on the image.

    Args:
        image (np.ndarray): The image to draw on
        region (tuple): Region coordinates (left, top, width, height)
        name (str, optional): Name to label the region
        color (tuple): BGR color for the region (default: green)

    Returns:
        np.ndarray: Image with region visualization
    """
    vis_image = image.copy()
    left, top, width, height = region

    # Draw rectangle
    cv2.rectangle(vis_image, (left, top), (left + width, top + height), color, 2)

    # Add label if name provided
    if name:
        cv2.putText(
            vis_image, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2
        )

    return vis_image


def show_regions(screenshot: np.ndarray, regions: dict[str, tuple[int, int, int, int]]):
    """Show all upgrade-related regions on the screenshot.

    Args:
        screenshot (np.ndarray): The captured screenshot
        regions (dict): Dictionary of region names and their coordinates
    """
    # Define colors for different regions

    # Start with the screenshot
    vis_image = screenshot.copy()

    # Add each region
    for name, region in regions.items():
        logger.debug(f"Adding region {name} to image")
        vis_image = add_region_to_image(vis_image, region, name, (0, 255, 0))

    # Show the visualization
    cv2.namedWindow("Selected Regions", cv2.WINDOW_NORMAL)
    cv2.imshow("Selected Regions", vis_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
