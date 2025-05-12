import cv2
import numpy as np
from pathlib import Path
from loguru import logger
import click
import sys


def calculate_average_colors(
    image_paths: list[Path] | list[str] | Path | str,
) -> dict[str, tuple[float, float, float]]:
    """Calculate the average BGR color for each image in the list.

    Args:
        image_paths: Can be:
            - A list of Path objects
            - A list of string paths
            - A single Path object
            - A single string path

    Returns:
        Dict[str, Tuple[float, float, float]]: Dictionary mapping image names to their average BGR colors
    """
    results = {}

    # Convert single path to list
    if isinstance(image_paths, (str, Path)):
        image_paths = [image_paths]

    # Convert all paths to Path objects
    paths = [Path(p) if isinstance(p, str) else p for p in image_paths]

    for path in paths:
        try:
            image = cv2.imread(str(path))
            if image is None:
                logger.warning(f"Could not read image: {path}")
                continue

            # Calculate average color
            avg_color = cv2.mean(image)[:3]  # Get BGR values, ignore alpha if present
            results[path.name] = avg_color

        except Exception as e:
            logger.error(f"Error processing {path}: {str(e)}")
            continue

    return results


@click.command()
@click.argument(
    "directory", type=click.Path(exists=True, file_okay=False, dir_okay=True)
)
@click.option(
    "--pattern", default="*.png", help="Glob pattern to match images (default: *.png)"
)
@click.option(
    "--recursive", "-r", is_flag=True, help="Recursively search subdirectories"
)
def main(directory: str, pattern: str, recursive: bool):
    """Calculate average colors of images in a directory."""
    directory = Path(directory)

    # Collect all image paths
    if recursive:
        image_paths = list(directory.rglob(pattern))
    else:
        image_paths = list(directory.glob(pattern))

    if not image_paths:
        logger.error(f"No images found in '{directory}' matching pattern '{pattern}'!")
        sys.exit(1)

    # Calculate and display average colors
    colors = calculate_average_colors(image_paths)

    # Calculate overall average color
    all_colors = np.array(list(colors.values()))
    avg_color = np.mean(all_colors, axis=0)
    print("\nOverall average color:")
    print(f"B={avg_color[0]:.1f}, G={avg_color[1]:.1f}, R={avg_color[2]:.1f}")

    # Print summary
    print(f"\nSummary of average colors in '{directory}':")
    print("-" * 50)
    for name, color in colors.items():
        print(f"{name}: B={color[0]:.1f}, G={color[1]:.1f}, R={color[2]:.1f}")


if __name__ == "__main__":
    main()
