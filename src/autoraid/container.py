"""Dependency injection container for AutoRaid services."""

from dependency_injector import containers, providers
import diskcache

from autoraid.autoupgrade.state_machine import UpgradeStateMachine
from autoraid.services.cache_service import CacheService
from autoraid.services.screenshot_service import ScreenshotService
from autoraid.services.locate_region_service import LocateRegionService


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
    cache_service = providers.Singleton(
        CacheService,
        cache=disk_cache,
    )

    screenshot_service = providers.Singleton(
        ScreenshotService,
    )

    locate_region_service = providers.Singleton(
        LocateRegionService,
        cache_service=cache_service,
        screenshot_service=screenshot_service,
    )

    # Factory services (new instance per operation)
    state_machine = providers.Factory(
        UpgradeStateMachine,
        max_attempts=config.max_attempts.as_(int),
    )
