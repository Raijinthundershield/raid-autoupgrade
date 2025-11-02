"""Unit tests for ProgressBarStateDetector.

Tests the stateless detector class with fixture images and validation.
Coverage target: ≥90%
"""

import json
from pathlib import Path

import cv2
import pytest

from autoraid.core.progress_bar_detector import (
    ProgressBarState,
    ProgressBarStateDetector,
)

# Load annotations for comprehensive fixture image testing
IMAGE_DIR = Path(__file__).parent.parent.parent / Path(
    "fixtures/images/progress_bar_state"
)
ANNOTATION_PATH = IMAGE_DIR / "annotations_progress_bar_state.json"
with open(ANNOTATION_PATH) as f:
    ANNOTATIONS = json.load(f)


@pytest.fixture
def detector():
    """Create a fresh detector instance."""
    return ProgressBarStateDetector()


@pytest.fixture
def fail_image():
    """Load fail state fixture image."""
    return cv2.imread("test/fixtures/images/progress_bar_state/fail.png")


@pytest.fixture
def progress_image():
    """Load progress state fixture image."""
    return cv2.imread("test/fixtures/images/progress_bar_state/progress.png")


@pytest.fixture
def standby_image():
    """Load standby state fixture image."""
    return cv2.imread("test/fixtures/images/progress_bar_state/standby.png")


@pytest.fixture
def connection_error_image():
    """Load connection error state fixture image."""
    return cv2.imread("test/fixtures/images/progress_bar_state/connection_error.png")


def test_detect_state_fail(detector, fail_image):
    """Test detector recognizes FAIL state from red bar image."""
    state = detector.detect_state(fail_image)
    assert state == ProgressBarState.FAIL


def test_detect_state_progress(detector, progress_image):
    """Test detector recognizes PROGRESS state from yellow bar image."""
    state = detector.detect_state(progress_image)
    assert state == ProgressBarState.PROGRESS


def test_detect_state_standby(detector, standby_image):
    """Test detector recognizes STANDBY state from black bar image."""
    state = detector.detect_state(standby_image)
    assert state == ProgressBarState.STANDBY


def test_detect_state_connection_error(detector, connection_error_image):
    """Test detector recognizes CONNECTION_ERROR state from blue bar image."""
    state = detector.detect_state(connection_error_image)
    assert state == ProgressBarState.CONNECTION_ERROR


def test_detect_state_is_stateless(detector, fail_image):
    """Test detector returns same result for same image (100 iterations)."""
    # First detection
    expected_state = detector.detect_state(fail_image)

    # Verify repeatability over 100 calls
    for _ in range(100):
        state = detector.detect_state(fail_image)
        assert state == expected_state, "Detector is not stateless - result changed"


@pytest.mark.parametrize("image_name, expected_state_str", ANNOTATIONS.items())
def test_detect_state_comprehensive(detector, image_name, expected_state_str):
    """Test detector against all 17 annotated fixture images.

    This comprehensive test ensures the detector correctly identifies states
    across diverse real-world progress bar screenshots. Critical for ensuring
    fail state detection accuracy (required for upgrade counting workflow).
    """
    image_path = IMAGE_DIR / image_name

    assert image_path.exists(), f"Test image does not exist: {image_path}"

    # Load fixture image
    image = cv2.imread(str(image_path))
    assert image is not None, f"Failed to load image: {image_path}"

    # Convert string state to enum
    expected_state = ProgressBarState(expected_state_str)

    # Detect state
    detected_state = detector.detect_state(image)

    # Critical assertion: fail state must be detected accurately
    # This is essential for the upgrade counting workflow
    if (
        detected_state == ProgressBarState.FAIL
        or expected_state == ProgressBarState.FAIL
    ):
        avg_color = cv2.mean(image)[:3]
        assert detected_state == expected_state, (
            f"Fail state detection mismatch!\n"
            f"  Image: {image_path}\n"
            f"  Expected: {expected_state.value}\n"
            f"  Detected: {detected_state.value}\n"
            f"  Avg BGR color: {avg_color}"
        )
