"""Upgrade workflows panel component.

Provides Count and Spend upgrade workflow UI with real-time progress display.
"""

import asyncio

from dependency_injector.wiring import Provide, inject
from loguru import logger
from nicegui import app, ui

from autoraid.container import Container
from autoraid.exceptions import (
    WindowNotFoundException,
    NetworkAdapterError,
    UpgradeWorkflowError,
)
from autoraid.logging_config import add_logger_sink
from autoraid.services.upgrade_orchestrator import UpgradeOrchestrator


MAX_COUNT_ATTEMPTS = 99

MAX_LOG_LINES = 1000

DEFAULT_MAX_ATTEMPTS = 1


def handle_workflow_error(
    error: Exception,
    workflow_name: str,
    logger_instance,
) -> None:
    """Centralized error handling for workflows.

    This function provides consistent error handling and user notifications
    for all exceptions that can occur during Count and Spend workflows.

    Args:
        error: The exception that was raised during workflow execution
        workflow_name: "Count" or "Spend" for logging context
        logger_instance: Logger instance to use for error logging
    """
    if isinstance(error, WindowNotFoundException):
        logger_instance.error(f"Window not found: {error}")
        ui.notify(
            "Raid window not found. Please ensure Raid is running.",
            type="negative",
        )
        return

    if isinstance(error, NetworkAdapterError):
        logger_instance.error(f"Network adapter error: {error}")
        ui.notify(f"Network adapter error: {error}", type="negative")
        return

    if isinstance(error, ConnectionError):
        logger_instance.error(f"No internet access: {error}")
        ui.notify(
            "No internet access. Please check your connection and try again.",
            type="negative",
        )
        return

    if isinstance(error, UpgradeWorkflowError):
        logger_instance.error(f"Workflow error: {error}")
        ui.notify(f"Workflow error: {error}", type="negative")
        return

    if isinstance(error, ValueError):
        logger_instance.error(f"Region error: {error}")
        ui.notify(
            "No regions cached. Please select regions first.",
            type="negative",
        )
        return

    if isinstance(error, asyncio.CancelledError):
        logger_instance.warning(f"{workflow_name} workflow cancelled by user")
        ui.notify(f"{workflow_name} workflow cancelled", type="warning")
        return

    # Unexpected errors
    logger_instance.exception(f"Unexpected error in {workflow_name} workflow: {error}")
    ui.notify(f"Unexpected error: {error}", type="negative")


@inject
def create_upgrade_panel(
    orchestrator: UpgradeOrchestrator = Provide[Container.upgrade_orchestrator],
    debug: bool = False,
) -> None:
    """Create the upgrade workflows panel (Count + Spend).

    Args:
        orchestrator: Injected UpgradeOrchestrator service for workflow execution
        debug: Enable debug logging (DEBUG level vs INFO level)
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

                async def start_count_workflow():
                    """Start count workflow asynchronously."""
                    nonlocal current_count_value, is_count_running

                    # Validate network adapter selection
                    selected_adapters = app.storage.user.get("selected_adapters", [])
                    if not selected_adapters:
                        ui.notify(
                            "Please select at least one network adapter before starting Count workflow",
                            type="warning",
                        )
                        return

                    if is_count_running or is_spend_running:
                        ui.notify("Workflow already running", type="warning")
                        return

                    # Clear logs when starting new workflow
                    log_element.clear()

                    current_count_value = 0
                    show_current_count.refresh()

                    start_button.props("disabled")
                    is_count_running = True

                    try:
                        logger.info("Starting count workflow from GUI")

                        n_fails, reason = await asyncio.to_thread(
                            orchestrator.count_workflow,
                            network_adapter_id=selected_adapters
                            if selected_adapters
                            else None,
                            max_attempts=99,
                            debug_dir=None,
                        )

                        current_count_value = n_fails
                        show_current_count.refresh()

                        app.storage.user["last_count_result"] = n_fails
                        show_max_attempts_input.refresh()

                        reason_text = reason.name if reason else "unknown"
                        ui.notify(
                            f"Count completed: {n_fails} fails (reason: {reason_text})",
                            type="positive",
                        )
                        logger.info(f"Count workflow completed: {n_fails} fails")

                    except Exception as e:
                        handle_workflow_error(e, "Count", logger)

                    finally:
                        start_button.props(remove="disabled")
                        is_count_running = False

                start_button.on_click(start_count_workflow)

            # Spend section (right)
            with ui.card().classes("flex-1"):
                ui.label("Spend Counted Attempts").classes("text-lg font-semibold")

                ui.space()

                # Max attempts input with auto-populate from last count
                max_attempts_input = None

                @ui.refreshable
                def show_max_attempts_input():
                    """Display max attempts input field (refreshable for auto-update)."""
                    nonlocal max_attempts_input
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

                show_max_attempts_input()

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
                    log_element.clear()

                    current_spent_value = 0
                    show_current_spent.refresh()

                    spend_button.props("disabled")
                    is_spend_running = True

                    try:
                        logger.info("Starting spend workflow from GUI")

                        n_upgrades, n_attempts, n_remaining = await asyncio.to_thread(
                            orchestrator.spend_workflow,
                            max_attempts=max_attempts,
                            continue_upgrade=continue_upgrade,
                            debug_dir=None,
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

                    except Exception as e:
                        handle_workflow_error(e, "Spend", logger)

                    finally:
                        # Re-enable spend button
                        spend_button.props(remove="disabled")
                        is_spend_running = False

                # Wire button handler
                spend_button.on_click(start_spend_workflow)

        ui.space()

        # Shared log section (bottom) for both workflows
        with ui.card().classes("w-full"):
            ui.label("Logs").classes("text-lg font-semibold")
            ui.space()
            log_element = ui.log(max_lines=1000).classes(
                "w-full h-64 bg-gray-900 text-white"
            )

            def gui_sink(msg):
                log_element.push(msg)

            add_logger_sink(debug, gui_sink, colorize=False)
