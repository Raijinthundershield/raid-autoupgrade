"""Main NiceGUI application for AutoRaid desktop interface."""

from nicegui import ui

from autoraid.gui.components.network_panel import create_network_panel
from autoraid.gui.components.region_panel import create_region_panel
from autoraid.gui.components.upgrade_panel import create_upgrade_panel


def main() -> None:
    """Launch the AutoRaid GUI in native desktop window mode."""

    @ui.page("/")
    def index():
        ui.label("AutoRaid Web Interface").classes("text-2xl font-bold")

        ui.separator()

        # Upgrade Workflows section (top)
        create_upgrade_panel()

        ui.separator()

        # Region Management section (middle)
        create_region_panel()

        ui.separator()

        # Network Adapters section (bottom)
        create_network_panel()

    ui.run(
        native=True,
        window_size=(800, 600),
        title="AutoRaid",
        reload=False,
        storage_secret="autoraid-gui-secret",  # Required for app.storage.user
    )


if __name__ == "__main__":
    main()
