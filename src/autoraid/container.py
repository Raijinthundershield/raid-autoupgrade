"""Dependency injection container for AutoRaid services."""

from dependency_injector import containers, providers
import diskcache

from autoraid.core.progress_bar_detector import ProgressBarStateDetector
from autoraid.core.progress_bar_monitor import ProgressBarMonitor
from autoraid.services.app_data import AppData
from autoraid.services.network import NetworkManager
from autoraid.services.cache_service import CacheService
from autoraid.services.screenshot_service import ScreenshotService
from autoraid.services.locate_region_service import LocateRegionService
from autoraid.services.window_interaction_service import WindowInteractionService
from autoraid.services.upgrade_orchestrator import UpgradeOrchestrator
from autoraid.workflows.count_workflow import CountWorkflow
from autoraid.workflows.spend_workflow import SpendWorkflow
from autoraid.workflows.debug_monitor_workflow import DebugMonitorWorkflow


class Container(containers.DeclarativeContainer):
    """Application dependency injection container.

    This container manages all service dependencies and their lifecycles.
    Services are registered as either Singletons (shared instances) or
    Factories (new instance per request).
    """

    # Wiring configuration for automatic dependency injection
    wiring_config = containers.WiringConfiguration(
        modules=[
            "autoraid.cli.upgrade_cli",
            "autoraid.cli.network_cli",
            "autoraid.cli.debug_cli",
            "autoraid.gui.app",
            "autoraid.gui.components.network_panel",
            "autoraid.gui.components.region_panel",
            "autoraid.gui.components.upgrade_panel",
        ]
    )

    # Configuration provider for application settings
    config = providers.Configuration()

    # External dependencies
    disk_cache = providers.Singleton(
        diskcache.Cache,
        directory=config.cache_dir,
    )

    # Singleton services (shared instance across application)
    app_data = providers.Singleton(
        AppData,
        cache_dir=config.cache_dir,
        debug_enabled=config.debug,
    )

    cache_service = providers.Singleton(
        CacheService,
        cache=disk_cache,
    )

    window_interaction_service = providers.Singleton(
        WindowInteractionService,
    )

    screenshot_service = providers.Singleton(
        ScreenshotService,
        window_interaction_service=window_interaction_service,
    )

    locate_region_service = providers.Singleton(
        LocateRegionService,
        cache_service=cache_service,
        screenshot_service=screenshot_service,
    )

    network_manager = providers.Singleton(
        NetworkManager,
    )

    progress_bar_detector = providers.Singleton(
        ProgressBarStateDetector,
    )

    # Factory services (new instance per operation)
    progress_bar_monitor = providers.Factory(
        ProgressBarMonitor,
        detector=progress_bar_detector,
    )

    upgrade_orchestrator = providers.Factory(
        UpgradeOrchestrator,
        screenshot_service=screenshot_service,
        window_interaction_service=window_interaction_service,
        cache_service=cache_service,
        network_manager=network_manager,
        monitor=progress_bar_monitor,
    )

    # Workflow factories (new instances with runtime parameters)
    count_workflow_factory = providers.Factory(
        CountWorkflow,
        cache_service=cache_service,
        window_interaction_service=window_interaction_service,
        network_manager=network_manager,
        orchestrator=upgrade_orchestrator,
    )

    spend_workflow_factory = providers.Factory(
        SpendWorkflow,
        orchestrator=upgrade_orchestrator,
        cache_service=cache_service,
        window_interaction_service=window_interaction_service,
        network_manager=network_manager,
    )

    debug_monitor_workflow_factory = providers.Factory(
        DebugMonitorWorkflow,
        orchestrator=upgrade_orchestrator,
        cache_service=cache_service,
        window_interaction_service=window_interaction_service,
        network_manager=network_manager,
    )
