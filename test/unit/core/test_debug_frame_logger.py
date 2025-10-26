"""Unit tests for DebugFrameLogger."""

import tempfile
import json
from pathlib import Path
import numpy as np
import pytest

from autoraid.core.debug_frame_logger import DebugFrameLogger
from autoraid.core.progress_bar_detector import ProgressBarState


class TestDebugFrameLogger:
    """Tests for DebugFrameLogger class."""

    def test_session_directory_creation(self):
        """Verify session directory is created on initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = DebugFrameLogger(
                output_dir=Path(tmpdir), session_name="test_session"
            )

            assert logger.session_dir.exists()
            assert logger.session_dir.is_dir()
            assert logger.session_dir.name == "test_session"

    def test_log_frame_saves_files_with_correct_naming(self):
        """Verify log_frame creates files with timestamp and state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = DebugFrameLogger(
                output_dir=Path(tmpdir), session_name="test_session"
            )

            fake_screenshot = np.zeros((100, 200, 3), dtype=np.uint8)
            fake_roi = np.zeros((50, 200, 3), dtype=np.uint8)

            logger.log_frame(
                frame_number=0,
                detected_state=ProgressBarState.FAIL,
                fail_count=1,
                screenshot=fake_screenshot,
                roi=fake_roi,
            )

            # Check files exist
            session_dir = logger.session_dir
            files = list(session_dir.glob("*.png"))
            assert len(files) == 2  # screenshot + roi

            # Check filenames contain state
            filenames = [f.name for f in files]
            assert any("fail" in name.lower() for name in filenames)
            assert any("screenshot" in name.lower() for name in filenames)
            assert any("roi" in name.lower() for name in filenames)

    def test_save_summary_creates_json_file(self):
        """Verify save_summary creates JSON file with correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = DebugFrameLogger(
                output_dir=Path(tmpdir), session_name="test_session"
            )

            fake_screenshot = np.zeros((100, 200, 3), dtype=np.uint8)
            fake_roi = np.zeros((50, 200, 3), dtype=np.uint8)

            # Log a few frames
            for i in range(3):
                logger.log_frame(
                    frame_number=i,
                    detected_state=ProgressBarState.PROGRESS,
                    fail_count=0,
                    screenshot=fake_screenshot,
                    roi=fake_roi,
                )

            # Save summary
            summary_path = logger.save_summary(metadata={"test_key": "test_value"})

            # Verify file exists
            assert summary_path.exists()
            assert summary_path.name == "debug_summary.json"

            # Verify JSON structure
            with open(summary_path) as f:
                summary = json.load(f)

            assert summary["session_name"] == "test_session"
            assert summary["total_frames"] == 3
            assert len(summary["frames"]) == 3
            assert summary["test_key"] == "test_value"

            # Verify frame structure
            frame = summary["frames"][0]
            assert "timestamp" in frame
            assert "frame_number" in frame
            assert "detected_state" in frame
            assert "fail_count" in frame
            assert "screenshot_file" in frame
            assert "roi_file" in frame
            assert "avg_color_bgr" in frame

    def test_frame_count_property(self):
        """Verify frame_count property tracks logged frames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = DebugFrameLogger(
                output_dir=Path(tmpdir), session_name="test_session"
            )

            fake_screenshot = np.zeros((100, 200, 3), dtype=np.uint8)
            fake_roi = np.zeros((50, 200, 3), dtype=np.uint8)

            assert logger.frame_count == 0

            logger.log_frame(
                frame_number=0,
                detected_state=ProgressBarState.PROGRESS,
                fail_count=0,
                screenshot=fake_screenshot,
                roi=fake_roi,
            )

            assert logger.frame_count == 1

            logger.log_frame(
                frame_number=1,
                detected_state=ProgressBarState.FAIL,
                fail_count=1,
                screenshot=fake_screenshot,
                roi=fake_roi,
            )

            assert logger.frame_count == 2

    def test_session_dir_property(self):
        """Verify session_dir property returns correct path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = DebugFrameLogger(
                output_dir=Path(tmpdir), session_name="test_session"
            )

            assert logger.session_dir == Path(tmpdir) / "test_session"

    def test_auto_generated_session_name(self):
        """Verify session name is auto-generated if not provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = DebugFrameLogger(output_dir=Path(tmpdir))

            # Session name should be auto-generated (timestamp format)
            assert logger.session_dir.name is not None
            assert len(logger.session_dir.name) > 0

    def test_calculate_avg_color(self):
        """Verify _calculate_avg_color returns correct BGR tuple."""
        # Create ROI with known color (red = 100, green = 50, blue = 25)
        roi = np.full((50, 200, 3), [25, 50, 100], dtype=np.uint8)

        avg_color = DebugFrameLogger._calculate_avg_color(roi)

        assert len(avg_color) == 3
        # BGR order
        assert avg_color[0] == pytest.approx(25.0, abs=1.0)  # Blue
        assert avg_color[1] == pytest.approx(50.0, abs=1.0)  # Green
        assert avg_color[2] == pytest.approx(100.0, abs=1.0)  # Red

    def test_log_frame_records_metadata_correctly(self):
        """Verify log_frame records all metadata correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = DebugFrameLogger(
                output_dir=Path(tmpdir), session_name="test_session"
            )

            fake_screenshot = np.zeros((100, 200, 3), dtype=np.uint8)
            fake_roi = np.full((50, 200, 3), [25, 50, 100], dtype=np.uint8)

            logger.log_frame(
                frame_number=5,
                detected_state=ProgressBarState.FAIL,
                fail_count=3,
                screenshot=fake_screenshot,
                roi=fake_roi,
            )

            # Check internal frame list
            assert len(logger._frames) == 1
            frame = logger._frames[0]

            assert frame.frame_number == 5
            assert frame.detected_state == "fail"
            assert frame.fail_count == 3
            assert frame.screenshot_file.endswith("_fail_screenshot.png")
            assert frame.roi_file.endswith("_fail_roi.png")
            assert len(frame.avg_color_bgr) == 3

    def test_multiple_frames_logged(self):
        """Verify multiple frames can be logged correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = DebugFrameLogger(
                output_dir=Path(tmpdir), session_name="test_session"
            )

            fake_screenshot = np.zeros((100, 200, 3), dtype=np.uint8)
            fake_roi = np.zeros((50, 200, 3), dtype=np.uint8)

            states = [
                ProgressBarState.PROGRESS,
                ProgressBarState.FAIL,
                ProgressBarState.STANDBY,
            ]

            for i, state in enumerate(states):
                logger.log_frame(
                    frame_number=i,
                    detected_state=state,
                    fail_count=i,
                    screenshot=fake_screenshot,
                    roi=fake_roi,
                )

            assert logger.frame_count == 3

            # Verify all files saved
            png_files = list(logger.session_dir.glob("*.png"))
            assert len(png_files) == 6  # 3 screenshots + 3 ROIs

    def test_save_summary_without_metadata(self):
        """Verify save_summary works without additional metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = DebugFrameLogger(
                output_dir=Path(tmpdir), session_name="test_session"
            )

            fake_screenshot = np.zeros((100, 200, 3), dtype=np.uint8)
            fake_roi = np.zeros((50, 200, 3), dtype=np.uint8)

            logger.log_frame(
                frame_number=0,
                detected_state=ProgressBarState.PROGRESS,
                fail_count=0,
                screenshot=fake_screenshot,
                roi=fake_roi,
            )

            summary_path = logger.save_summary()

            assert summary_path.exists()

            with open(summary_path) as f:
                summary = json.load(f)

            assert "session_name" in summary
            assert "total_frames" in summary
            assert "frames" in summary
