"""Session selector component for choosing monitoring sessions to review."""

from collections.abc import Callable
from pathlib import Path

from loguru import logger
from nicegui import ui

from autoraid.debug.utils import get_available_sessions


def create_session_selector(
    cache_dir: Path, on_session_loaded: Callable[[Path], None]
) -> None:
    """Create session selector UI component.

    Args:
        cache_dir: Root cache directory to search for sessions
        on_session_loaded: Callback function when session is loaded, receives session_path
    """
    with ui.card().classes("w-full mb-4"):
        ui.label("Select Monitoring Session").classes("text-xl font-bold")

        sessions = get_available_sessions(cache_dir)
        logger.info(f"Found {len(sessions)} monitoring sessions")

        if not sessions:
            ui.label("No monitoring sessions found.").classes("text-orange-600")
            ui.label("Run 'uv run autoraid debug progressbar' to create one.")
            ui.label(f"Searched in: {cache_dir}").classes("text-xs text-gray-500")
        else:
            ui.label(f"Found {len(sessions)} session(s)").classes(
                "text-sm text-gray-600"
            )

            session_select = ui.select(
                options={str(s): s.name for s in sessions},
                label="Session",
                value=str(sessions[0]) if sessions else None,
            )

            ui.button(
                "Load Session",
                on_click=lambda: on_session_loaded(Path(session_select.value)),
            )
