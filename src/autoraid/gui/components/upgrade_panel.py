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
from autoraid.gui.utils import set_log_element, setup_log_streaming, clear_logs
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
    current_spent_value = 0
    is_count_running = False
    is_spend_running = False

    with ui.column().classes("w-full"):
        # Section header
        ui.label("Upgrade Workflows").classes("text-xl font-bold")

        ui.space()

        # Count and Spend sections side-by-side
        with ui.row().classes("w-full gap-4"):
            # Count section (left)
            with ui.card().classes("flex-1"):
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
                    ui.label(f"Count: {current_count_value}").classes(
                        "text-lg font-bold"
                    )

                show_current_count()

                ui.space()

                start_button = ui.button("Start Count", color="primary")

                def validate_and_start_count():
                    """Validate inputs and start count workflow."""
                    # Validate network adapter selection before starting async task
                    selected_adapters = app.storage.user.get("selected_adapters", [])
                    if not selected_adapters:
                        ui.notify(
                            "Please select at least one network adapter before starting Count workflow",
                            type="warning",
                        )
                        return

                    # Validation passed, create async task
                    asyncio.create_task(start_count_workflow())

                async def start_count_workflow():
                    """Start count workflow asynchronously."""
                    nonlocal current_count_value, is_count_running

                    if is_count_running or is_spend_running:
                        ui.notify("Workflow already running", type="warning")
                        return

                    selected_adapters = app.storage.user.get("selected_adapters", [])

                    # Clear logs when starting new workflow
                    clear_logs()

                    current_count_value = 0
                    show_current_count.refresh()

                    start_button.props("disabled")
                    is_count_running = True

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
                        start_button.props(remove="disabled")
                        is_count_running = False

                start_button.on_click(validate_and_start_count)

            # Spend section (right)
            with ui.card().classes("flex-1"):
                ui.label("Spend Counted Attempts").classes("text-lg font-semibold")

                ui.space()

                # Max attempts input with auto-populate from last count
                last_count = app.storage.user.get("last_count_result")
                max_attempts_input = ui.number(
                    label="Max Attempts",
                    value=last_count if last_count is not None else 1,
                    min=1,
                    step=1,
                ).classes("w-full")
                # Add tooltip
                with max_attempts_input:
                    ui.tooltip(
                        "Number of upgrade attempts to spend (auto-populated from Count workflow)"
                    )

                ui.space()

                # Continue upgrade checkbox
                continue_upgrade_checkbox = ui.checkbox(
                    "Continue Upgrade (level 10+ gear)"
                ).props("dense")
                # Add tooltip
                with continue_upgrade_checkbox:
                    ui.tooltip(
                        "Enable for artifacts level 10+, which continue to next upgrade level after successful upgrade"
                    )

                ui.space()

                # Current spent display (refreshable for real-time updates)
                @ui.refreshable
                def show_current_spent():
                    """Display current spent value during workflow."""
                    ui.label(f"Current Spent: {current_spent_value}").classes(
                        "text-lg font-bold"
                    )

                show_current_spent()

                ui.space()

                spend_button = ui.button("Start Spend", color="secondary")

                async def start_spend_workflow():
                    """Start spend workflow asynchronously."""
                    nonlocal current_spent_value, is_spend_running

                    if is_count_running or is_spend_running:
                        ui.notify("Workflow already running", type="warning")
                        return

                    max_attempts = int(max_attempts_input.value or 1)
                    continue_upgrade = continue_upgrade_checkbox.value

                    # Clear logs when starting new workflow
                    clear_logs()

                    current_spent_value = 0
                    show_current_spent.refresh()

                    spend_button.props("disabled")
                    is_spend_running = True

                    try:
                        logger.info("Starting spend workflow from GUI")

                        debug_dir = None
                        if app.storage.user.get("debug_enabled", False):
                            debug_dir = Path("cache-raid-autoupgrade/debug")

                        n_upgrades, n_attempts, n_remaining = await asyncio.to_thread(
                            orchestrator.spend_workflow,
                            max_attempts=max_attempts,
                            continue_upgrade=continue_upgrade,
                            debug_dir=debug_dir,
                        )

                        current_spent_value = n_attempts
                        show_current_spent.refresh()

                        ui.notify(
                            f"Spend completed: {n_upgrades} upgrades, {n_attempts} attempts, {n_remaining} remaining",
                            type="positive",
                        )
                        logger.info(
                            f"Spend workflow completed: {n_upgrades} upgrades, {n_attempts} attempts"
                        )

                    except WindowNotFoundException as e:
                        logger.error(f"Window not found: {e}")
                        ui.notify(
                            "Raid window not found. Please ensure Raid is running.",
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

                    except ConnectionError as e:
                        logger.error(f"No internet access: {e}")
                        ui.notify(
                            "No internet access. Please check your connection and try again.",
                            type="negative",
                        )

                    except asyncio.CancelledError:
                        logger.warning("Spend workflow cancelled by user")
                        ui.notify("Spend workflow cancelled", type="warning")

                    except Exception as e:
                        logger.exception(f"Unexpected error in spend workflow: {e}")
                        ui.notify(
                            f"Unexpected error: {e}",
                            type="negative",
                        )

                    finally:
                        # Re-enable spend button
                        spend_button.props(remove="disabled")
                        is_spend_running = False

                # Wire button handler
                spend_button.on_click(
                    lambda: asyncio.create_task(start_spend_workflow())
                )

        ui.space()

        # Shared log section (bottom) for both workflows
        with ui.card().classes("w-full"):
            ui.label("Workflow Logs").classes("text-lg font-semibold")
            ui.space()
            log_element = ui.log(max_lines=1000).classes("w-full h-64")

            # Set up log streaming to this element
            set_log_element(log_element)
            setup_log_streaming()
