"""Region management UI panel for selecting and viewing cached regions."""

import asyncio

import cv2
from dependency_injector.wiring import Provide, inject
from loguru import logger
from nicegui import ui

from autoraid.container import Container
from autoraid.exceptions import WindowNotFoundException
from autoraid.protocols import (
    CacheProtocol,
    LocateRegionProtocol,
    ScreenshotProtocol,
    WindowInteractionProtocol,
)

WINDOW_TITLE = "Raid: Shadow Legends"
WINDOW_CHECK_INTERVAL = 5.0  # seconds


@inject
def create_region_panel(
    locate_region_service: LocateRegionProtocol = Provide[
        Container.locate_region_service
    ],
    screenshot_service: ScreenshotProtocol = Provide[Container.screenshot_service],
    window_interaction_service: WindowInteractionProtocol = Provide[
        Container.window_interaction_service
    ],
    cache_service: CacheProtocol = Provide[Container.cache_service],
) -> None:
    """Create region management UI section.

    Args:
        locate_region_service: Service for region detection and selection
        screenshot_service: Service for screenshot operations
        window_interaction_service: Service for window interaction operations
        cache_service: Service for caching regions
    """
    logger.debug("Creating region panel")

    # Component state
    state = {
        "current_window_size": None,
        "cached_window_size": None,
        "cached_regions": [],
        "window_found": True,
        "size_mismatch": False,
    }

    def update_window_status():
        """Update window size and cached region status."""
        try:
            # Get current window size
            window_size = window_interaction_service.get_window_size(WINDOW_TITLE)
            state["current_window_size"] = window_size
            state["window_found"] = True

            # Get cached regions for current window size
            cached_regions_dict = cache_service.get_regions(window_size)
            if cached_regions_dict:
                state["cached_regions"] = list(cached_regions_dict.keys())
                state["cached_window_size"] = window_size
            else:
                state["cached_regions"] = []
                state["cached_window_size"] = None

            # Check if window size changed
            if (
                state["cached_window_size"]
                and window_size != state["cached_window_size"]
            ):
                state["size_mismatch"] = True
            else:
                state["size_mismatch"] = False

        except WindowNotFoundException:
            state["window_found"] = False
            state["current_window_size"] = None

        # Refresh UI displays
        show_window_size.refresh()
        show_region_status.refresh()
        show_warning_banner.refresh()

    @ui.refreshable
    def show_window_size():
        """Display current window size."""
        if state["window_found"] and state["current_window_size"]:
            width, height = state["current_window_size"]
            ui.label(f"Current Window Size: {width} x {height}")
        elif not state["window_found"]:
            ui.label("⚠ Raid window not found").classes("text-red-500")

    @ui.refreshable
    def show_region_status():
        """Display cached regions status."""
        if state["cached_regions"]:
            regions_str = ", ".join(state["cached_regions"])
            ui.label(f"✓ Cached Regions: Found ({regions_str})").classes(
                "text-green-500"
            )
        else:
            ui.label("✗ Cached Regions: Not Found").classes("text-red-500")

    @ui.refreshable
    def show_warning_banner():
        """Show warning banner if window size changed."""
        if state["size_mismatch"]:
            with ui.banner().classes("bg-yellow-100"):
                ui.label(
                    "⚠ Window size changed. Cached regions invalid. Please re-select regions."
                ).classes("text-yellow-800")

    async def async_show_regions():
        """Show cached regions in OpenCV window."""
        try:
            # Validate window exists
            window_size = window_interaction_service.get_window_size(WINDOW_TITLE)

            # Get cached regions
            cached_regions_dict = cache_service.get_regions(window_size)
            if not cached_regions_dict:
                ui.notify(
                    "No cached regions found. Please select regions first.",
                    type="warning",
                )
                return

            # Take screenshot
            screenshot = screenshot_service.take_screenshot(WINDOW_TITLE)

            # Draw regions on screenshot
            annotated = screenshot.copy()
            colors = {"upgrade_bar": (0, 255, 0), "upgrade_button": (255, 0, 0)}
            for name, region in cached_regions_dict.items():
                left, top, width, height = region
                color = colors.get(name, (0, 0, 255))
                cv2.rectangle(
                    annotated,
                    (left, top),
                    (left + width, top + height),
                    color,
                    2,
                )
                cv2.putText(
                    annotated,
                    name,
                    (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2,
                )

            # Show in OpenCV window (blocking)
            def show_opencv_window():
                cv2.imshow("Cached Regions", annotated)
                cv2.waitKey(0)
                cv2.destroyAllWindows()

            await asyncio.to_thread(show_opencv_window)

        except WindowNotFoundException:
            ui.notify(
                "Raid window not found. Check if Raid is running.", type="negative"
            )
        except Exception as e:
            logger.error(f"Error showing regions: {e}")
            ui.notify(f"Error showing regions: {e}", type="negative")

    async def async_select_regions_auto():
        """Select regions using automatic detection with manual fallback."""
        try:
            # Validate window exists
            window_interaction_service.get_window_size(WINDOW_TITLE)

            # Take screenshot
            screenshot = screenshot_service.take_screenshot(WINDOW_TITLE)

            # Run region selection in thread (OpenCV blocks)
            def select_regions():
                return locate_region_service.get_regions(screenshot, manual=False)

            regions = await asyncio.to_thread(select_regions)

            # Update status
            update_window_status()

            # Check if automatic detection succeeded
            if regions:
                ui.notify("Regions detected automatically", type="positive")
            else:
                ui.notify(
                    "Automatic detection failed. Regions selected manually.",
                    type="info",
                )

        except WindowNotFoundException:
            ui.notify(
                "Raid window not found. Check if Raid is running.", type="negative"
            )
        except Exception as e:
            logger.error(f"Error selecting regions (auto): {e}")
            ui.notify(f"Region detection failed: {e}", type="negative")

    async def async_select_regions_manual():
        """Select regions using manual ROI selection."""
        try:
            # Validate window exists
            window_interaction_service.get_window_size(WINDOW_TITLE)

            # Take screenshot
            screenshot = screenshot_service.take_screenshot(WINDOW_TITLE)

            # Run manual selection in thread (OpenCV blocks)
            def select_regions():
                return locate_region_service.get_regions(
                    screenshot, manual=True, override_cache=True
                )

            await asyncio.to_thread(select_regions)

            # Update status
            update_window_status()

            ui.notify("Regions selected manually", type="positive")

        except WindowNotFoundException:
            ui.notify(
                "Raid window not found. Check if Raid is running.", type="negative"
            )
        except Exception as e:
            logger.error(f"Error selecting regions (manual): {e}")
            ui.notify(f"Region selection failed: {e}", type="negative")

    # Create UI
    with ui.card().classes("w-full"):
        ui.label("Region Management").classes("text-xl font-bold")

        # Status displays
        with ui.column():
            show_window_size()
            show_region_status()

        # Warning banner
        show_warning_banner()

        # Action buttons
        with ui.row():
            ui.button("Show Regions", on_click=async_show_regions).props(
                'tooltip="Display annotated screenshot with cached regions highlighted"'
            ).bind_enabled_from(state, "cached_regions", backward=lambda x: len(x) > 0)

            # NOTE: Automatic detection currently broken. Enable when fixed.
            # ui.button(
            #     "Select Regions (Auto)", on_click=async_select_regions_auto
            # ).props(
            #     'tooltip="Attempt automatic region detection. Falls back to manual selection if fails."'
            # )

            ui.button(
                "Select Regions (Manual)", on_click=async_select_regions_manual
            ).props(
                'tooltip="Manually draw ROIs for upgrade bar, button, and artifact icon"'
            )

    # Set up timer for window status monitoring
    ui.timer(interval=WINDOW_CHECK_INTERVAL, callback=update_window_status)

    # Initial status update
    update_window_status()

    logger.debug("Region panel created")
