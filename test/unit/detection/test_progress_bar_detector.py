"""Unit tests for ProgressBarStateDetector.

Tests the stateless detector class with fixture images and validation.
Coverage target: ≥90%
"""

from pathlib import Path

import cv2
import pytest

from raid_autoupgrade.detection.progress_bar_detector import (
    ProgressBarState,
    ProgressBarStateDetector,
)
from raid_autoupgrade.detection.sample_annotation import discover_labeled_samples

# Samples self-describe their label via a per-image sidecar JSON; the suite
# discovers them by globbing. `skip` samples (single-frame-ambiguous dim
# progress, deferred to #38) are present for inspection but not asserted.
IMAGE_DIR = Path(__file__).parent.parent.parent / Path(
    "fixtures/images/progress_bar_state"
)
ASSERTABLE_SAMPLES = [s for s in discover_labeled_samples(IMAGE_DIR) if s.is_assertable]


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


@pytest.mark.parametrize("sample", ASSERTABLE_SAMPLES, ids=lambda s: s.image_path.name)
def test_detect_state_comprehensive(detector, sample):
    """Detector matches the recorded label for every assertable sample.

    Discovered by globbing per-image sidecars, this asserts *every* label
    (not just FAIL), closing the previously-untested progress<->standby gap.
    """
    image = cv2.imread(str(sample.image_path))
    assert image is not None, f"Failed to load image: {sample.image_path}"

    expected_state = ProgressBarState(sample.annotation.label)
    detected_state = detector.detect_state(image)

    assert detected_state == expected_state, (
        f"State detection mismatch!\n"
        f"  Image: {sample.image_path}\n"
        f"  Expected: {expected_state.value}\n"
        f"  Detected: {detected_state.value}\n"
        f"  Avg BGR color: {cv2.mean(image)[:3]}"
    )
