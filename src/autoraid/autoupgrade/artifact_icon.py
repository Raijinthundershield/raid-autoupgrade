from loguru import logger
import cv2
import pytesseract
import numpy as np


def get_rank(screenshot: np.ndarray) -> int:
    """
    Get the rank of the artifact. Counts the amount of stars in the artifact icon.
    """
    logger.warning("Not implemented")
    return 0


def get_level(screenshot: np.ndarray) -> int:
    """
    Get the level of the artifact by OCR.
    """

    # Convert to grayscale for better OCR
    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

    # Threshold to get black text
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

    # OCR the image
    try:
        text = pytesseract.image_to_string(
            thresh, config="--psm 7 -c tessedit_char_whitelist=0123456789"
        )
        level = int(text.strip())
        return level
    except ValueError:
        logger.warning("Could not read artifact level")
        return 0
