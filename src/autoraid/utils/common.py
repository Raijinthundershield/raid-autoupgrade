from datetime import datetime


def get_timestamp() -> str:
    """Get current timestamp in a format suitable for filenames.

    Returns:
        str: Timestamp string in format YYYYMMDD_HHMMSS
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")
