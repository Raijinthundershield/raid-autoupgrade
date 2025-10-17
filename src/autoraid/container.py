"""Dependency injection container for AutoRaid services."""

from dependency_injector import containers, providers
import diskcache


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
