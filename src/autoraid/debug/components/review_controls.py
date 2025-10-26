"""Review controls component for true state selection and frame navigation."""

from collections.abc import Callable
from dataclasses import dataclass

from nicegui import ui

from autoraid.core.progress_bar_detector import ProgressBarState


@dataclass
class ReviewControls:
    """Handle for updating review control components."""

    true_state_dropdown: ui.select
    frame_navigation_label: ui.label

    def set_true_state(self, state: str | None) -> None:
        """Set true state dropdown value without triggering on_change.

        Args:
            state: State value to set, or None for "Not Reviewed"
        """
        self.true_state_dropdown.set_value(state or "None")

    def set_frame_label(self, frame_idx: int, total_frames: int) -> None:
        """Update frame navigation label.

        Args:
            frame_idx: Current frame index (0-based)
            total_frames: Total number of frames
        """
        self.frame_navigation_label.set_text(f"Frame {frame_idx + 1}/{total_frames}")


def create_review_controls(
    on_state_changed: Callable[[str], None],
    on_prev: Callable[[], None],
    on_next: Callable[[], None],
) -> ReviewControls:
    """Create review controls UI component.

    Args:
        on_state_changed: Callback when true state is changed, receives state value
        on_prev: Callback when previous button clicked
        on_next: Callback when next button clicked

    Returns:
        ReviewControls handle for updating displays
    """
    # Review card - True State Selection
    with ui.card().classes("w-full mt-4"):
        ui.label("Manual Review").classes("text-xl font-bold")
        ui.separator()

        with ui.row().classes("items-center gap-4"):
            ui.label("True State:").classes("font-semibold")

            true_state_dropdown = ui.select(
                options={
                    "None": "Not Reviewed",
                    ProgressBarState.FAIL.value: "Fail",
                    ProgressBarState.PROGRESS.value: "Progress",
                    ProgressBarState.STANDBY.value: "Standby",
                    ProgressBarState.CONNECTION_ERROR.value: "Connection Error",
                    ProgressBarState.UNKNOWN.value: "Unknown",
                },
                label="Select true state",
                value="None",
                on_change=lambda e: on_state_changed(e.value),
            )

    # Navigation
    with ui.card().classes("w-full mt-4"):
        with ui.row().classes("w-full justify-between items-center"):
            ui.button("← Previous", on_click=on_prev)
            frame_navigation_label = ui.label("Frame 0/0").classes("text-lg")
            ui.button("Next →", on_click=on_next)

    return ReviewControls(
        true_state_dropdown=true_state_dropdown,
        frame_navigation_label=frame_navigation_label,
    )
