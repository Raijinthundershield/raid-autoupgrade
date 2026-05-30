from datetime import datetime


def get_timestamp() -> str:
    """Get current timestamp in a format suitable for filenames.

    Includes milliseconds to ensure uniqueness when capturing multiple
    frames per second (e.g., progress bar monitoring at 5 FPS).

    Returns:
        str: Timestamp string in format YYYYMMDD_HHMMSS_mmm (with milliseconds)
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Keep only 3 digits (ms)
