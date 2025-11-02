"""Progress bar state detector review GUI.

This module provides a NiceGUI interface for reviewing and validating
progress bar state detection results from monitoring sessions.

This is the main coordinator that wires together UI components and business logic.
"""

from pathlib import Path

import cv2
from loguru import logger
from nicegui import ui

from autoraid.detection.progress_bar_detector import ProgressBarStateDetector
from autoraid.debug.components import (
    create_accuracy_panel,
    create_frame_viewer,
    create_review_controls,
    create_session_selector,
)
from autoraid.debug.models import ReviewSession


class ProgressBarReviewGUI:
    """Main coordinator for progress bar state detector review GUI.

    This class coordinates between UI components and business logic models.
    It acts as a thin "glue" layer that handles callbacks and updates.
    """

    def __init__(self, cache_dir: Path):
        """Initialize the GUI coordinator.

        Args:
            cache_dir: Path to cache directory containing monitoring sessions
        """
        self.cache_dir = cache_dir

        # Business logic (no UI dependencies)
        self.session = ReviewSession()
        self.detector = ProgressBarStateDetector()

        # UI component handles (set during render)
        self.frame_viewer = None
        self.review_controls = None
        self.accuracy_panel = None

    def render(self) -> None:
        """Render the complete GUI interface."""
        ui.label("Progress Bar State Detector Review").classes(
            "text-3xl font-bold mb-4"
        )

        # Create UI components
        create_session_selector(self.cache_dir, self._on_session_loaded)
        self.frame_viewer = create_frame_viewer(self.detector)
        self.review_controls = create_review_controls(
            on_state_changed=self._on_state_changed,
            on_prev=self._on_prev,
            on_next=self._on_next,
        )
        self.accuracy_panel = create_accuracy_panel()

        # Add keyboard navigation (arrow keys with wraparound)
        ui.keyboard(on_key=self._on_key_press)

    def _on_session_loaded(self, session_path: Path) -> None:
        """Handle session loaded event.

        Args:
            session_path: Path to the loaded session directory
        """
        self.session.load_session(session_path)
        ui.notify(
            f"Loaded session: {session_path.name} ({self.session.total_frames} frames)"
        )
        self._refresh_all()

    def _on_state_changed(self, state: str) -> None:
        """Handle true state changed event.

        Args:
            state: New state value ("None" or state name)
        """
        true_state = None if state == "None" else state
        self.session.save_true_state(true_state)
        ui.notify(f"Saved true state: {state}")

        # Update accuracy panel after state change
        if self.accuracy_panel and self.session.is_loaded:
            self.accuracy_panel.update(self.session.frames, self._on_frame_clicked)

    def _on_prev(self) -> None:
        """Handle previous button/key press (with wraparound)."""
        if self.session.prev_frame():
            self._refresh_frame_display()

    def _on_next(self) -> None:
        """Handle next button/key press (with wraparound)."""
        if self.session.next_frame():
            self._refresh_frame_display()

    def _on_key_press(self, event) -> None:
        """Handle keyboard events for navigation.

        Args:
            event: Keyboard event with 'key' and 'action' attributes
        """
        if not self.session.is_loaded:
            return

        # Only handle keydown events (not keyup) and ignore repeat (key held)
        if not event.action.keydown or event.action.repeat:
            return

        key = event.key

        if key == "ArrowRight":
            self._on_next()
        elif key == "ArrowLeft":
            self._on_prev()

    def _on_frame_clicked(self, frame_idx: int) -> None:
        """Handle frame table row click.

        Args:
            frame_idx: Index of clicked frame (0-based)
        """
        if self.session.jump_to_frame(frame_idx):
            self._refresh_frame_display()
            ui.notify(f"Jumped to frame {frame_idx + 1}")

    def _refresh_all(self) -> None:
        """Refresh all UI components with current session data."""
        if not self.session.is_loaded:
            return

        self._refresh_frame_display()

        # Update accuracy panel
        if self.accuracy_panel:
            self.accuracy_panel.update(self.session.frames, self._on_frame_clicked)

    def _refresh_frame_display(self) -> None:
        """Refresh frame viewer and controls for current frame."""
        if not self.session.is_loaded:
            return

        frame = self.session.current_frame
        if frame is None:
            return

        # Load images from disk
        screenshot_path = self.session.review_dir / frame.screenshot_file
        roi_path = self.session.review_dir / frame.roi_file

        # Debug logging
        logger.debug(
            f"Loading frame {self.session.current_frame_idx + 1}/{self.session.total_frames}: "
            f"screenshot={frame.screenshot_file}, roi={frame.roi_file}"
        )

        screenshot = cv2.imread(str(screenshot_path))
        roi = cv2.imread(str(roi_path))

        # Check for null images (file read failures)
        if screenshot is None:
            logger.error(f"Failed to load screenshot: {screenshot_path}")
            ui.notify(
                f"Error loading screenshot for frame {self.session.current_frame_idx + 1}",
                type="negative",
            )
            return

        if roi is None:
            logger.error(f"Failed to load ROI: {roi_path}")
            ui.notify(
                f"Error loading ROI for frame {self.session.current_frame_idx + 1}",
                type="negative",
            )
            return

        # Update frame viewer
        if self.frame_viewer:
            self.frame_viewer.update(
                frame,
                screenshot,
                roi,
                self.session.current_frame_idx,
                self.session.total_frames,
            )

        # Update review controls
        if self.review_controls:
            self.review_controls.set_true_state(frame.true_state)
            self.review_controls.set_frame_label(
                self.session.current_frame_idx, self.session.total_frames
            )
