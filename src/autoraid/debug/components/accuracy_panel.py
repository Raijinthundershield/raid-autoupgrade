"""Accuracy panel component for displaying detection accuracy summary and frames table."""

from collections.abc import Callable
from dataclasses import dataclass

from nicegui import ui

from autoraid.debug.models import AccuracyCalculator
from autoraid.workflows.progressbar_monitor_workflow import ReviewedFrameMetadata


@dataclass
class AccuracyPanel:
    """Handle for updating accuracy panel components."""

    accuracy_summary_container: ui.column
    frames_table_container: ui.column

    def update(
        self,
        frames: list[ReviewedFrameMetadata],
        on_frame_clicked: Callable[[int], None],
    ) -> None:
        """Update accuracy summary and frames table.

        Args:
            frames: List of all frames in session
            on_frame_clicked: Callback when frame row is clicked, receives frame_idx
        """
        stats = AccuracyCalculator.calculate_stats(frames)

        # Update accuracy summary
        self._update_summary(stats)

        # Update frames table
        self._update_table(frames, on_frame_clicked)

    def _update_summary(self, stats: dict) -> None:
        """Update accuracy summary display."""
        self.accuracy_summary_container.clear()
        with self.accuracy_summary_container:
            ui.label("Detection Accuracy Summary").classes("text-xl font-bold")
            ui.separator()

            # Overall stats
            with ui.grid(columns=2).classes("gap-2 w-full mb-4"):
                ui.label("Total Frames:").classes("font-semibold")
                ui.label(str(stats["total_frames"]))

                ui.label("Reviewed Frames:").classes("font-semibold")
                ui.label(str(stats["reviewed_frames"]))

                ui.label("Correct Detections:").classes("font-semibold")
                ui.label(str(stats["correct"])).classes("text-green-600")

                ui.label("Incorrect Detections:").classes("font-semibold")
                ui.label(str(stats["incorrect"])).classes("text-red-600")

                ui.label("Overall Accuracy:").classes("font-semibold")
                accuracy = stats["overall_accuracy"]
                color = AccuracyCalculator.get_accuracy_color(accuracy)
                ui.label(f"{accuracy:.1f}%").classes(f"text-{color}-600 font-bold")

            # Per-state breakdown
            if stats["per_state"]:
                ui.separator()
                ui.label("Per-State Accuracy").classes("text-lg font-semibold mt-2")

                for state, state_stats in sorted(stats["per_state"].items()):
                    with ui.card().classes("w-full bg-gray-50 mt-2"):
                        ui.label(state.upper()).classes(
                            f"font-semibold text-{AccuracyCalculator.get_state_color(state)}"
                        )
                        with ui.grid(columns=2).classes("gap-1 text-sm"):
                            ui.label("Total:")
                            ui.label(str(state_stats["total"]))
                            ui.label("Correct:")
                            ui.label(str(state_stats["correct"])).classes(
                                "text-green-600"
                            )
                            ui.label("Incorrect:")
                            ui.label(str(state_stats["incorrect"])).classes(
                                "text-red-600"
                            )
                            ui.label("Accuracy:")
                            acc = state_stats["accuracy"]
                            color = AccuracyCalculator.get_accuracy_color(acc)
                            ui.label(f"{acc:.1f}%").classes(
                                f"text-{color}-600 font-bold"
                            )

    def _update_table(
        self,
        frames: list[ReviewedFrameMetadata],
        on_frame_clicked: Callable[[int], None],
    ) -> None:
        """Update frames table display."""
        self.frames_table_container.clear()
        with self.frames_table_container:
            ui.label("Frame Detection Results").classes("text-xl font-bold")
            ui.separator()

            # Scrollable container for table
            with ui.column().classes("w-full h-96 overflow-auto"):
                # Table header
                with ui.row().classes("font-bold gap-2 sticky top-0 bg-white"):
                    ui.label("#").classes("w-12")
                    ui.label("Timestamp").classes("w-32")
                    ui.label("Detected").classes("w-24")
                    ui.label("True State").classes("w-24")
                    ui.label("Match").classes("w-16")

                # Table rows
                for idx, frame in enumerate(frames):
                    match_icon, match_color = AccuracyCalculator.get_match_icon(
                        frame.detected_state, frame.true_state
                    )

                    # Make row clickable
                    with (
                        ui.row()
                        .classes("gap-2 hover:bg-gray-100 cursor-pointer items-center")
                        .on("click", lambda i=idx: on_frame_clicked(i))
                    ):
                        ui.label(str(idx + 1)).classes("w-12 text-sm")
                        ui.label(
                            AccuracyCalculator.format_timestamp(frame.timestamp)
                        ).classes("w-32 text-xs")
                        ui.label(frame.detected_state).classes(
                            f"w-24 text-xs text-{AccuracyCalculator.get_state_color(frame.detected_state)}"
                        )
                        ui.label(
                            frame.true_state if frame.true_state else "Not Reviewed"
                        ).classes(
                            f"w-24 text-xs text-{AccuracyCalculator.get_state_color(frame.true_state)}"
                        )
                        ui.label(match_icon).classes(f"w-16 text-{match_color}")


def create_accuracy_panel() -> AccuracyPanel:
    """Create accuracy panel UI component (summary + table side-by-side).

    Returns:
        AccuracyPanel handle for updating displays
    """
    # Accuracy panel - Summary and Frames Table side by side
    with ui.row().classes("w-full gap-4 mt-4"):
        # Left: Accuracy Summary
        with ui.card().classes("flex-1"):
            accuracy_summary_container = ui.column().classes("w-full")

        # Right: Frames Table (wider)
        with ui.card().classes("flex-[2]"):
            frames_table_container = ui.column().classes("w-full")

    return AccuracyPanel(
        accuracy_summary_container=accuracy_summary_container,
        frames_table_container=frames_table_container,
    )
