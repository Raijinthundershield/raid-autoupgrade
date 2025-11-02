"""Debug frame logging for progress bar monitoring.

This module provides optional debug data capture during monitoring
without polluting the orchestrator.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import cv2
import numpy as np
from loguru import logger

from autoraid.detection.progress_bar_detector import ProgressBarState
from autoraid.utils.common import get_timestamp


@dataclass
class DebugFrame:
    """Single frame of debug data captured during monitoring."""

    timestamp: str
    frame_number: int
    detected_state: str
    fail_count: int
    screenshot_file: str
    roi_file: str
    avg_color_bgr: tuple[float, float, float]


class DebugFrameLogger:
    """Captures and saves debug data during progress bar monitoring"""

    def __init__(self, output_dir: Path, session_name: str | None = None):
        """Initialize logger with output directory.

        Args:
            output_dir: Base directory for debug output
            session_name: Optional session name (default: timestamp)
        """
        self._session_name = session_name or get_timestamp()
        self._session_dir = output_dir / self._session_name
        self._session_dir.mkdir(parents=True, exist_ok=True)

        self._frames: list[DebugFrame] = []

        logger.info(f"DebugFrameLogger initialized: {self._session_dir}")

    def log_frame(
        self,
        frame_number: int,
        detected_state: ProgressBarState,
        fail_count: int,
        screenshot: np.ndarray,
        roi: np.ndarray,
    ) -> None:
        """Log a single frame with all debug data.

        Args:
            frame_number: Sequential frame number (0-indexed)
            detected_state: Detected ProgressBarState
            fail_count: Current fail count
            screenshot: Full window screenshot (BGR)
            roi: Progress bar ROI (BGR)
        """
        timestamp = get_timestamp()
        state_name = detected_state.value

        # Calculate average color from ROI
        # Reuses same method as ProgressBarStateDetector for consistency
        avg_color = self._calculate_avg_color(roi)

        # Save screenshot
        screenshot_filename = f"{timestamp}_{state_name}_screenshot.png"
        screenshot_path = self._session_dir / screenshot_filename
        cv2.imwrite(str(screenshot_path), screenshot)

        # Save ROI
        roi_filename = f"{timestamp}_{state_name}_roi.png"
        roi_path = self._session_dir / roi_filename
        cv2.imwrite(str(roi_path), roi)

        # Record metadata
        frame = DebugFrame(
            timestamp=timestamp,
            frame_number=frame_number,
            detected_state=state_name,
            fail_count=fail_count,
            screenshot_file=screenshot_filename,
            roi_file=roi_filename,
            avg_color_bgr=avg_color,
        )
        self._frames.append(frame)

        # Log progress periodically
        if (frame_number + 1) % 10 == 0:
            logger.debug(f"DebugFrameLogger: {frame_number + 1} frames captured")

    @staticmethod
    def _calculate_avg_color(roi: np.ndarray) -> tuple[float, float, float]:
        return cv2.mean(roi)[:3]

    def save_summary(self, metadata: dict | None = None) -> Path:
        summary = {
            "session_name": self._session_name,
            "total_frames": len(self._frames),
            "frames": [asdict(frame) for frame in self._frames],
        }

        if metadata:
            summary.update(metadata)

        summary_path = self._session_dir / "debug_summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"DebugFrameLogger: Saved summary to {summary_path}")
        return summary_path

    @property
    def session_dir(self) -> Path:
        return self._session_dir

    @property
    def frame_count(self) -> int:
        return len(self._frames)
