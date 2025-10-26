"""Frame viewer component for displaying images, metadata, and detector results."""

import base64
import time
from dataclasses import dataclass

import cv2
import numpy as np
from nicegui import ui

from autoraid.core.progress_bar_detector import ProgressBarStateDetector
from autoraid.debug.models import AccuracyCalculator
from autoraid.workflows.progressbar_monitor_workflow import ReviewedFrameMetadata


@dataclass
class FrameViewer:
    """Handle for updating frame viewer components."""

    screenshot_img: ui.image
    roi_img: ui.image
    metadata_container: ui.column
    detector_results_container: ui.column
    detector: ProgressBarStateDetector

    def update(
        self,
        frame: ReviewedFrameMetadata,
        screenshot: np.ndarray,
        roi: np.ndarray,
        frame_idx: int,
        total_frames: int,
    ) -> None:
        """Update all frame viewer displays.

        Args:
            frame: Frame metadata to display
            screenshot: Screenshot image (BGR)
            roi: Progress bar ROI image (BGR)
            frame_idx: Current frame index (0-based)
            total_frames: Total number of frames
        """
        # Update images
        self._update_images(screenshot, roi)

        # Update metadata
        self._update_metadata(frame, frame_idx, total_frames)

        # Update detector results
        self._update_detector_results(roi)

    def _update_images(self, screenshot: np.ndarray, roi: np.ndarray) -> None:
        """Update screenshot and ROI image displays.

        Note: cv2.imencode for PNG automatically converts BGR to RGB during encoding,
        so we should NOT pre-convert. If we do, colors get double-swapped.

        Cache-busting: Adds a timestamp fragment to force browser to reload images
        even when rapidly switching between frames.
        """
        # Encode BGR images directly - imencode handles BGR->RGB conversion for PNG
        _, screenshot_buf = cv2.imencode(".png", screenshot)
        _, roi_buf = cv2.imencode(".png", roi)

        screenshot_b64 = base64.b64encode(screenshot_buf).decode("utf-8")
        roi_b64 = base64.b64encode(roi_buf).decode("utf-8")

        # Add cache-busting timestamp to force browser refresh
        timestamp = int(time.time() * 1000)  # Milliseconds for uniqueness

        self.screenshot_img.set_source(
            f"data:image/png;base64,{screenshot_b64}#{timestamp}"
        )
        self.roi_img.set_source(f"data:image/png;base64,{roi_b64}#{timestamp}")

    def _update_metadata(
        self, frame: ReviewedFrameMetadata, frame_idx: int, total_frames: int
    ) -> None:
        """Update metadata display card."""
        self.metadata_container.clear()
        with self.metadata_container:
            ui.label(f"Frame {frame_idx + 1}/{total_frames}").classes(
                "text-xl font-bold"
            )
            ui.separator()

            with ui.grid(columns=2).classes("gap-2 w-full"):
                ui.label("Timestamp:").classes("font-semibold")
                ui.label(frame.timestamp)

                ui.label("Detected State:").classes("font-semibold")
                ui.label(frame.detected_state).classes(
                    f"text-{AccuracyCalculator.get_state_color(frame.detected_state)}"
                )

                ui.label("Avg Color (BGR):").classes("font-semibold")
                ui.label(
                    f"({frame.avg_color_bgr[0]:.1f}, {frame.avg_color_bgr[1]:.1f}, {frame.avg_color_bgr[2]:.1f})"
                )

                ui.label("Screenshot:").classes("font-semibold")
                ui.label(frame.screenshot_file).classes("text-xs")

                ui.label("ROI File:").classes("font-semibold")
                ui.label(frame.roi_file).classes("text-xs")

    def _update_detector_results(self, roi: np.ndarray) -> None:
        """Run detector methods and display results."""
        self.detector_results_container.clear()
        with self.detector_results_container:
            ui.label("Detector Analysis").classes("text-xl font-bold")
            ui.separator()

            # Get average color
            avg_color = self.detector._avg_color(roi)

            # Run all state detection methods
            results = {
                "is_progress": self.detector._is_progress(avg_color),
                "is_fail": self.detector._is_fail(avg_color),
                "is_standby": self.detector._is_standby(avg_color),
                "is_connection_error": self.detector._is_connection_error(avg_color),
            }

            with ui.grid(columns=2).classes("gap-2 w-full"):
                for method_name, result in results.items():
                    ui.label(f"{method_name}:").classes("font-semibold")
                    icon = "✅" if result else "❌"
                    color = "green" if result else "red"
                    ui.label(f"{icon} {result}").classes(f"text-{color}-600")

            ui.separator()
            ui.label(
                f"Avg Color (BGR): ({avg_color[0]:.1f}, {avg_color[1]:.1f}, {avg_color[2]:.1f})"
            )


def create_frame_viewer(detector: ProgressBarStateDetector) -> FrameViewer:
    """Create frame viewer UI component (3-column layout).

    Args:
        detector: Progress bar state detector instance

    Returns:
        FrameViewer handle for updating displays
    """
    # Main content - 3 cards side by side
    with ui.row().classes("w-full gap-4"):
        # Card 1: Images
        with ui.card().classes("flex-1"):
            ui.label("Visual Review").classes("text-xl font-bold")
            ui.separator()

            ui.label("Screenshot:").classes("font-semibold mt-2")
            screenshot_img = ui.image().classes("w-full border")

            ui.label("Progress Bar ROI:").classes("font-semibold mt-4")
            roi_img = ui.image().classes("w-full border")

        # Card 2: Metadata
        with ui.card().classes("flex-1"):
            metadata_container = ui.column().classes("w-full")

        # Card 3: Detector Results
        with ui.card().classes("flex-1"):
            detector_results_container = ui.column().classes("w-full")

    return FrameViewer(
        screenshot_img=screenshot_img,
        roi_img=roi_img,
        metadata_container=metadata_container,
        detector_results_container=detector_results_container,
        detector=detector,
    )
