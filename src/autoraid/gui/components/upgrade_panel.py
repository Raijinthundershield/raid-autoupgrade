"""Upgrade workflows panel component.

Provides Count and Spend upgrade workflow UI with real-time progress display.
"""

import asyncio
from pathlib import Path

from dependency_injector.wiring import Provide, inject
from loguru import logger
from nicegui import app, ui

from autoraid.container import Container
from autoraid.exceptions import (
    WindowNotFoundException,
    NetworkAdapterError,
    UpgradeWorkflowError,
)
from autoraid.services.upgrade_orchestrator import UpgradeOrchestrator


@inject
def create_upgrade_panel(
    orchestrator: UpgradeOrchestrator = Provide[Container.upgrade_orchestrator],
) -> None:
    """Create the upgrade workflows panel (Count + Spend).

    Args:
        orchestrator: Injected UpgradeOrchestrator service for workflow execution
    """
    # Workflow state
    current_count_value = 0
    is_running = False

    with ui.column().classes("w-full"):
        # Section header
        ui.label("Upgrade Workflows").classes("text-xl font-bold")

        ui.space()

        # Count section
        with ui.card().classes("w-full"):
            ui.label("Count Upgrade Fails").classes("text-lg font-semibold")

            # Display selected network adapters (read-only)
            @ui.refreshable
            def show_selected_adapters():
                """Display selected network adapters from storage."""
                selected_ids = app.storage.user.get("selected_adapters", [])
                if selected_ids:
                    adapter_text = (
                        f"Selected Adapters: {', '.join(map(str, selected_ids))}"
                    )
                    ui.label(adapter_text).classes("text-sm text-gray-600")
                else:
                    ui.label("No network adapters selected").classes(
                        "text-sm text-yellow-600"
                    )

            show_selected_adapters()

            ui.space()

            # Current count display (refreshable for real-time updates)
            @ui.refreshable
            def show_current_count():
                """Display current count value during workflow."""
                ui.label(f"Current Count: {current_count_value}").classes(
                    "text-lg font-bold"
                )

            show_current_count()

            ui.space()

            start_button = ui.button("Start Count", color="primary")

            async def start_count_workflow():
                """Start count workflow asynchronously."""
                nonlocal current_count_value, is_running

                if is_running:
                    ui.notify("Workflow already running", type="warning")
                    return

                selected_adapters = app.storage.user.get("selected_adapters", [])

                current_count_value = 0
                show_current_count.refresh()

                start_button.props("disabled")
                is_running = True

                try:
                    logger.info("Starting count workflow from GUI")

                    debug_dir = None
                    if app.storage.user.get("debug_enabled", False):
                        debug_dir = Path("cache-raid-autoupgrade/debug")

                    n_fails, reason = await asyncio.to_thread(
                        orchestrator.count_workflow,
                        network_adapter_id=selected_adapters
                        if selected_adapters
                        else None,
                        max_attempts=99,
                        debug_dir=debug_dir,
                    )

                    current_count_value = n_fails
                    show_current_count.refresh()

                    app.storage.user["last_count_result"] = n_fails

                    reason_text = reason.name if reason else "unknown"
                    ui.notify(
                        f"Count completed: {n_fails} fails (reason: {reason_text})",
                        type="positive",
                    )
                    logger.info(f"Count workflow completed: {n_fails} fails")

                except WindowNotFoundException as e:
                    logger.error(f"Window not found: {e}")
                    ui.notify(
                        "Raid window not found. Please ensure Raid is running.",
                        type="negative",
                    )

                except NetworkAdapterError as e:
                    logger.error(f"Network adapter error: {e}")
                    ui.notify(
                        f"Network adapter error: {e}",
                        type="negative",
                    )

                except UpgradeWorkflowError as e:
                    logger.error(f"Workflow error: {e}")
                    ui.notify(
                        f"Workflow error: {e}",
                        type="negative",
                    )

                except ValueError as e:
                    logger.error(f"Region error: {e}")
                    ui.notify(
                        "No regions cached. Please select regions first.",
                        type="negative",
                    )

                except asyncio.CancelledError:
                    logger.warning("Count workflow cancelled by user")
                    ui.notify("Count workflow cancelled", type="warning")

                except Exception as e:
                    logger.exception(f"Unexpected error in count workflow: {e}")
                    ui.notify(
                        f"Unexpected error: {e}",
                        type="negative",
                    )

                finally:
                    # Re-enable start button
                    start_button.props(remove="disabled")
                    is_running = False

            # Wire button handler
            start_button.on_click(lambda: asyncio.create_task(start_count_workflow()))
