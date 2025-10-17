import click
import platform
import sys

from loguru import logger

from autoraid.platform.network import NetworkManager


@click.group()
def network():
    """Manage network adapters for the airplane mode trick."""
    pass


@network.command()
def list():
    """List all network adapters."""
    if not platform.system() == "Windows":
        logger.error("This command only works on Windows")
        sys.exit(1)

    manager = NetworkManager()
    adapters = manager.get_adapters()
    manager.display_adapters(adapters)


@network.command()
@click.argument("adapter", required=False)
def disable(adapter: str | None):
    """Disable selected network adapters.

    If ADAPTER is provided, it will try to find and disable that specific adapter.
    Otherwise, it will prompt you to select adapters interactively.
    """
    if not platform.system() == "Windows":
        logger.error("This command only works on Windows")
        sys.exit(1)

    manager = NetworkManager()
    if adapter:
        adapters = manager.get_adapters()
        found_adapter = manager.find_adapter(adapters, adapter)
        if not found_adapter:
            logger.error(f"No adapter found matching: {adapter}")
            sys.exit(1)
        if manager.toggle_adapter(found_adapter.id, False):
            logger.info(f"Successfully disabled adapter: {found_adapter.name}")
        else:
            logger.error(f"Failed to disable adapter: {found_adapter.name}")
    else:
        manager.toggle_selected_adapters(False)


@network.command()
@click.argument("adapter", required=False)
def enable(adapter: str | None):
    """Enable selected network adapters.

    If ADAPTER is provided, it will try to find and enable that specific adapter.
    Otherwise, it will prompt you to select adapters interactively.
    """
    if not platform.system() == "Windows":
        logger.error("This command only works on Windows")
        sys.exit(1)

    manager = NetworkManager()
    if adapter:
        adapters = manager.get_adapters()
        found_adapter = manager.find_adapter(adapters, adapter)
        if not found_adapter:
            logger.error(f"No adapter found matching: {adapter}")
            sys.exit(1)
        if manager.toggle_adapter(found_adapter.id, True):
            logger.info(f"Successfully enabled adapter: {found_adapter.name}")
        else:
            logger.error(f"Failed to enable adapter: {found_adapter.name}")
    else:
        manager.toggle_selected_adapters(True)
