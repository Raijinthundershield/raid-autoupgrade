"""Main NiceGUI application for AutoRaid desktop interface."""

from nicegui import ui


def main() -> None:
    """Launch the AutoRaid GUI in native desktop window mode."""

    @ui.page("/")
    def index():
        ui.label("AutoRaid Web Interface").classes("text-2xl font-bold")

    ui.run(
        native=True,
        window_size=(800, 600),
        title="AutoRaid",
        reload=False,
    )


if __name__ == "__main__":
    main()
