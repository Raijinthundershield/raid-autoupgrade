import cv2
import numpy as np
from pathlib import Path
from loguru import logger
import argparse
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


def main():
    parser = argparse.ArgumentParser(
        description="Calculate average colors of images in a directory"
    )
    parser.add_argument(
        "directory", type=str, help="Directory containing images to analyze"
    )
    parser.add_argument(
        "--pattern",
        default="*.png",
        help="Glob pattern to match images (default: *.png)",
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Recursively search subdirectories",
    )
    parser.add_argument(
        "--keywords",
        "-k",
        nargs="+",
        help="Keywords to match in filenames (e.g., 'fail' 'progress')",
    )

    args = parser.parse_args()
    directory = Path(args.directory)

    if not directory.is_dir():
        logger.error(f"'{directory}' is not a directory!")
        sys.exit(1)

    # Collect all image paths
    if args.recursive:
        image_paths = list(directory.rglob(args.pattern))
    else:
        image_paths = list(directory.glob(args.pattern))

    if not image_paths:
        logger.error(
            f"No images found in '{directory}' matching pattern '{args.pattern}'!"
        )
        sys.exit(1)

    # Filter by keywords if provided
    if args.keywords:
        filtered_paths = []
        for path in image_paths:
            if any(keyword.lower() in path.name.lower() for keyword in args.keywords):
                filtered_paths.append(path)

        if not filtered_paths:
            logger.error(f"No images found matching keywords: {args.keywords}")
            sys.exit(1)

        image_paths = filtered_paths
        logger.info(
            f"Found {len(image_paths)} images matching keywords: {args.keywords}"
        )

    # Calculate and display average colors
    colors = calculate_average_colors(image_paths)

    # Calculate overall average color
    all_colors = np.array(list(colors.values()))
    avg_color = np.mean(all_colors, axis=0)
    print("\nOverall average color:")
    print(f"B={avg_color[0]:.1f}, G={avg_color[1]:.1f}, R={avg_color[2]:.1f}")

    # Print summary
    print(f"\nSummary of average colors in '{directory}':")
    if args.keywords:
        print(f"Matching keywords: {args.keywords}")
    print("-" * 50)
    for name, color in colors.items():
        print(f"{name}: B={color[0]:.1f}, G={color[1]:.1f}, R={color[2]:.1f}")


if __name__ == "__main__":
    main()
