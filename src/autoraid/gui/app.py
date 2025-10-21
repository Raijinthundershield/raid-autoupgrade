"""Main NiceGUI application for AutoRaid desktop interface."""

from nicegui import ui
from dependency_injector.wiring import Provide, inject

from autoraid.gui.components.network_panel import create_network_panel
from autoraid.gui.components.region_panel import create_region_panel
from autoraid.gui.components.upgrade_panel import create_upgrade_panel
from autoraid.container import Container
from autoraid.services.window_interaction_service import WindowInteractionService
from autoraid.platform.network import NetworkManager
from autoraid.exceptions import WindowNotFoundException

WINDOW_TITLE = "Raid: Shadow Legends"
STATUS_UPDATE_INTERVAL = 1.0  # seconds


@inject
def create_header(
    window_interaction_service: WindowInteractionService = Provide[
        Container.window_interaction_service
    ],
) -> None:
    """Create application header with title and status indicators.

    Args:
        window_interaction_service: Service for checking window existence
    """
    network_manager = NetworkManager()

    with ui.card().classes("w-full bg-blue-50"):
        with ui.row().classes("w-full items-center justify-between"):
            # Application title
            ui.label("AutoRaid Upgrade Interface").classes("text-2xl font-bold")

            # Status indicators (right side)
            with ui.row().classes("gap-4 items-center"):

                @ui.refreshable
                def show_raid_window_status():
                    """Display Raid window status indicator."""
                    try:
                        window_interaction_service.get_window_size(WINDOW_TITLE)
                        ui.label("🟢 Raid Window").classes(
                            "text-green-600 font-semibold"
                        )
                    except WindowNotFoundException:
                        ui.label("🔴 Raid Window").classes("text-red-600 font-semibold")
                    except Exception:
                        ui.label("🟡 Raid Window").classes(
                            "text-yellow-600 font-semibold"
                        )

                show_raid_window_status()

                # Network status
                @ui.refreshable
                def show_network_status():
                    """Display network connection status indicator."""
                    try:
                        online = network_manager.check_network_access(timeout=2.0)
                        if online:
                            ui.label("🟢 Network").classes(
                                "text-green-600 font-semibold"
                            )
                        else:
                            ui.label("🔴 Network").classes("text-red-600 font-semibold")
                    except Exception:
                        ui.label("🟡 Network").classes("text-yellow-600 font-semibold")

                show_network_status()

        # Set up timer to update status indicators every 5 seconds
        ui.timer(
            STATUS_UPDATE_INTERVAL,
            lambda: [show_raid_window_status.refresh(), show_network_status.refresh()],
        )


def main(debug: bool = False) -> None:
    """Launch the AutoRaid GUI in native desktop window mode.

    Args:
        debug: Enable debug logging (same as --debug flag in CLI)
    """

    @ui.page("/")
    def index():
        # Single-page scrollable layout
        with ui.column().classes("w-full"):
            create_header()
            ui.separator()
            create_upgrade_panel(debug=debug)
            ui.separator()
            create_region_panel()
            ui.separator()
            create_network_panel()

    ui.run(
        native=True,
        window_size=(1216, 832),
        title="AutoRaid",
        reload=False,
        storage_secret="autoraid-gui-secret",  # Required for app.storage.user
    )


if __name__ == "__main__":
    main()
