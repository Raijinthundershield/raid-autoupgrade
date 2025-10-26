"""Business logic models for progress bar review GUI.

This module contains pure Python business logic with no UI dependencies,
making it testable and reusable.
"""

from pathlib import Path

from loguru import logger

from autoraid.debug.utils import (
    create_review_folder,
    load_monitor_log,
    load_reviewed_metadata,
    save_reviewed_metadata,
)
from autoraid.workflows.progressbar_monitor_workflow import ReviewedFrameMetadata


class ReviewSession:
    """Manages review session state and operations.

    This class handles loading sessions, navigating frames, and saving review data.
    It contains no UI code and can be tested independently.
    """

    def __init__(self):
        self.session_dir: Path | None = None
        self.review_dir: Path | None = None
        self.frames: list[ReviewedFrameMetadata] = []
        self.current_frame_idx: int = 0

    @property
    def current_frame(self) -> ReviewedFrameMetadata | None:
        """Get the current frame being reviewed."""
        if not self.frames or self.current_frame_idx >= len(self.frames):
            return None
        return self.frames[self.current_frame_idx]

    @property
    def total_frames(self) -> int:
        """Get total number of frames in session."""
        return len(self.frames)

    @property
    def is_loaded(self) -> bool:
        """Check if a session is currently loaded."""
        return self.session_dir is not None and len(self.frames) > 0

    def load_session(self, session_path: Path) -> None:
        """Load a monitoring session for review.

        Args:
            session_path: Path to the session directory
        """
        self.session_dir = session_path
        self.review_dir = create_review_folder(session_path)
        self.frames = load_reviewed_metadata(self.review_dir)
        self.current_frame_idx = 0

        logger.info(
            f"Loaded monitoring session: {session_path} ({len(self.frames)} frames)"
        )
        logger.info(f"Review directory: {self.review_dir}")

    def save_true_state(self, state: str | None) -> None:
        """Save the true state for current frame.

        Args:
            state: State value to save, or None to clear
        """
        if not self.is_loaded:
            logger.warning("Cannot save true state: no session loaded")
            return

        # Update frame metadata
        frame = self.frames[self.current_frame_idx]
        updated_frame_dict = {**frame.__dict__}
        updated_frame_dict["true_state"] = state

        self.frames[self.current_frame_idx] = ReviewedFrameMetadata(
            **updated_frame_dict
        )

        # Save to disk
        original_metadata = load_monitor_log(self.review_dir)
        save_reviewed_metadata(self.review_dir, self.frames, original_metadata)

        logger.debug(f"Frame {self.current_frame_idx}: Set true_state to {state}")

    def next_frame(self) -> bool:
        """Navigate to next frame with wraparound.

        Wraps from last frame to first frame.

        Returns:
            True if navigation succeeded, False if no session loaded
        """
        if not self.is_loaded:
            return False
        self.current_frame_idx = (self.current_frame_idx + 1) % len(self.frames)
        return True

    def prev_frame(self) -> bool:
        """Navigate to previous frame with wraparound.

        Wraps from first frame to last frame.

        Returns:
            True if navigation succeeded, False if no session loaded
        """
        if not self.is_loaded:
            return False
        self.current_frame_idx = (self.current_frame_idx - 1) % len(self.frames)
        return True

    def jump_to_frame(self, frame_idx: int) -> bool:
        """Navigate to a specific frame by index.

        Args:
            frame_idx: Index of frame to jump to (0-based)

        Returns:
            True if navigation succeeded, False if index invalid
        """
        if 0 <= frame_idx < len(self.frames):
            self.current_frame_idx = frame_idx
            logger.debug(f"Jumped to frame {frame_idx + 1}/{len(self.frames)}")
            return True
        return False


class AccuracyCalculator:
    """Calculates accuracy statistics for reviewed frames.

    This class provides static methods for calculating accuracy metrics
    and formatting helpers. No state is maintained.
    """

    @staticmethod
    def calculate_stats(frames: list[ReviewedFrameMetadata]) -> dict:
        """Calculate accuracy statistics from reviewed frames.

        Args:
            frames: List of frames to analyze

        Returns:
            Dictionary with overall and per-state accuracy statistics:
            {
                "total_frames": int,
                "reviewed_frames": int,
                "correct": int,
                "incorrect": int,
                "overall_accuracy": float,
                "per_state": {
                    "state_name": {
                        "total": int,
                        "correct": int,
                        "incorrect": int,
                        "accuracy": float
                    }
                }
            }
        """
        if not frames:
            return {
                "total_frames": 0,
                "reviewed_frames": 0,
                "correct": 0,
                "incorrect": 0,
                "overall_accuracy": 0.0,
                "per_state": {},
            }

        # Filter only reviewed frames (true_state is not None)
        reviewed_frames = [f for f in frames if f.true_state is not None]

        if not reviewed_frames:
            return {
                "total_frames": len(frames),
                "reviewed_frames": 0,
                "correct": 0,
                "incorrect": 0,
                "overall_accuracy": 0.0,
                "per_state": {},
            }

        # Calculate overall accuracy
        correct = sum(1 for f in reviewed_frames if f.detected_state == f.true_state)
        incorrect = len(reviewed_frames) - correct
        overall_accuracy = (
            (correct / len(reviewed_frames)) * 100 if reviewed_frames else 0.0
        )

        # Calculate per-state accuracy
        per_state = {}
        all_states = {f.true_state for f in reviewed_frames}

        for state in all_states:
            state_frames = [f for f in reviewed_frames if f.true_state == state]
            state_correct = sum(
                1 for f in state_frames if f.detected_state == f.true_state
            )
            state_accuracy = (
                (state_correct / len(state_frames)) * 100 if state_frames else 0.0
            )

            per_state[state] = {
                "total": len(state_frames),
                "correct": state_correct,
                "incorrect": len(state_frames) - state_correct,
                "accuracy": state_accuracy,
            }

        return {
            "total_frames": len(frames),
            "reviewed_frames": len(reviewed_frames),
            "correct": correct,
            "incorrect": incorrect,
            "overall_accuracy": overall_accuracy,
            "per_state": per_state,
        }

    @staticmethod
    def get_state_color(state: str | None) -> str:
        """Get Tailwind color class for state display.

        Args:
            state: Progress bar state name

        Returns:
            Tailwind color class (e.g., "red-600")
        """
        if state is None:
            return "gray-400"

        colors = {
            "fail": "red-600",
            "progress": "yellow-600",
            "standby": "gray-600",
            "connection_error": "blue-600",
            "unknown": "purple-600",
        }
        return colors.get(state, "gray-600")

    @staticmethod
    def get_accuracy_color(accuracy: float) -> str:
        """Get Tailwind color class based on accuracy percentage.

        Args:
            accuracy: Accuracy percentage (0-100)

        Returns:
            Tailwind color class (e.g., "green", "yellow", "red")
        """
        if accuracy >= 90.0:
            return "green"
        elif accuracy >= 70.0:
            return "yellow"
        else:
            return "red"

    @staticmethod
    def format_timestamp(timestamp: str) -> str:
        """Extract condensed timestamp for table display.

        Args:
            timestamp: Full timestamp string

        Returns:
            Condensed timestamp (last 8 characters or after underscore)
        """
        if "_" in timestamp:
            return timestamp.split("_")[1]
        return timestamp[-8:]

    @staticmethod
    def get_match_icon(detected: str, true_state: str | None) -> tuple[str, str]:
        """Get match icon and color for frame comparison.

        Args:
            detected: Detected state
            true_state: True (reviewed) state, or None if not reviewed

        Returns:
            Tuple of (icon, color_class)
        """
        if true_state is None:
            return "⚪", "gray-400"  # Not reviewed
        elif detected == true_state:
            return "✅", "green-600"  # Correct
        else:
            return "❌", "red-600"  # Incorrect
