"""Network adapter management panel for AutoRaid GUI."""

from dependency_injector.wiring import inject, Provide
from nicegui import app, ui
from loguru import logger

from autoraid.container import Container
from autoraid.platform.network import NetworkManager


@inject
def create_network_panel(
    network_manager: NetworkManager = Provide[Container.network_manager],
) -> None:
    """Create network adapter management UI section.

    Displays:
    - Internet status indicator (green=online, red=offline)
    - Network adapters table with multi-select checkboxes
    - Refresh button to reload adapter status

    State:
    - Selected adapter IDs persist in app.storage.user['selected_adapters']

    Args:
        network_manager: Injected NetworkManager singleton service
    """

    # Initialize storage for selected adapters
    if "selected_adapters" not in app.storage.user:
        app.storage.user["selected_adapters"] = []

    with ui.column().classes("w-full"):
        # Section header
        ui.label("Network Adapters").classes("text-xl font-bold")

        # Internet status indicator (updated via timer)
        @ui.refreshable
        def show_internet_status():
            """Display internet connection status with color coding."""
            try:
                from autoraid.platform.network import NetworkState

                state = network_manager.check_network_access(timeout=2.0)
                is_online = state == NetworkState.ONLINE
                icon = "🟢" if is_online else "🔴"
                color = "text-green-600" if is_online else "text-red-600"
                status_text = "Online" if is_online else "Offline"
                ui.label(f"{icon} Internet: {status_text}").classes(color)
            except Exception as e:
                logger.error(f"Failed to check internet status: {e}")
                ui.label("🟡 Internet: Unknown").classes("text-yellow-600")

        show_internet_status()

        # Poll internet status every 5 seconds
        ui.timer(5.0, lambda: show_internet_status.refresh())

        ui.space()

        # Network adapters table (refreshable)
        @ui.refreshable
        def show_adapter_table():
            """Display network adapters table with multi-select checkboxes."""
            try:
                adapters = network_manager.get_adapters()

                with ui.column().classes("w-full"):
                    # Table header
                    with ui.row().classes("font-bold gap-4"):
                        ui.label("Select").classes("w-16")
                        ui.label("ID").classes("w-16")
                        ui.label("Name").classes("w-64")
                        ui.label("Status").classes("w-24")

                    # Table rows
                    for adapter in adapters:
                        with ui.row().classes("gap-4 items-center"):
                            # Checkbox for adapter selection
                            selected_adapters = app.storage.user.get(
                                "selected_adapters", []
                            )
                            checkbox = ui.checkbox(
                                value=adapter.id in selected_adapters,
                            ).classes("w-16")

                            # Bind checkbox to selection handler
                            # Use lambda with default argument to capture adapter.id
                            checkbox.on(
                                "update:model-value",
                                lambda e, aid=adapter.id: on_adapter_select(
                                    aid, e.args
                                ),
                            )

                            # Adapter info
                            ui.label(adapter.id).classes("w-16")
                            ui.label(adapter.name).classes("w-64")

                            # Status with color coding
                            if adapter.enabled:
                                ui.label("Enabled").classes("w-24 text-green-600")
                            else:
                                ui.label("Disabled").classes("w-24 text-red-600")

            except Exception as e:
                logger.error(f"Failed to load adapters: {e}")
                ui.label("Failed to load network adapters").classes("text-red-600")

        show_adapter_table()

        ui.space()

        # Refresh button
        with ui.row().classes("gap-2"):
            ui.button("Refresh", on_click=lambda: refresh_adapters()).props("outlined")

    def on_adapter_select(adapter_id: str, checked: bool) -> None:
        """Update selected adapters list when checkbox toggled.

        Args:
            adapter_id: Network adapter ID
            checked: True if checkbox checked, False otherwise
        """
        selected = app.storage.user.get("selected_adapters", [])

        if checked and adapter_id not in selected:
            selected.append(adapter_id)
            logger.debug(f"Selected adapter: {adapter_id}")
        elif not checked and adapter_id in selected:
            selected.remove(adapter_id)
            logger.debug(f"Deselected adapter: {adapter_id}")

        app.storage.user["selected_adapters"] = selected

    def refresh_adapters() -> None:
        """Reload adapter table and internet status."""
        try:
            show_adapter_table.refresh()
            show_internet_status.refresh()
            ui.notify("Adapters refreshed", type="positive")
        except Exception as e:
            logger.error(f"Failed to refresh adapters: {e}")
            ui.notify("Failed to refresh adapters", type="negative")
