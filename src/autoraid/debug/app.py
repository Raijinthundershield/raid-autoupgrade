"""Main entry point for debug GUI applications."""

from pathlib import Path

from nicegui import ui

from autoraid.debug.progressbar_review_gui import ProgressBarReviewGUI


def main(cache_dir: Path | str = "cache-raid-autoupgrade") -> None:
    """Launch the progress bar review GUI.

    Args:
        cache_dir: Path to cache directory (default: "cache-raid-autoupgrade")
    """
    cache_path = Path(cache_dir) if isinstance(cache_dir, str) else cache_dir

    @ui.page("/")
    def index():
        gui = ProgressBarReviewGUI(cache_path)
        gui.render()

    ui.run(
        title="AutoRaid - Progress Bar Review",
        native=True,
        window_size=(1600, 900),
        frameless=False,
        reload=False,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
