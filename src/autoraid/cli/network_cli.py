import click
import platform
import sys

from dependency_injector.wiring import inject, Provide
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

from autoraid.container import Container
from autoraid.services.network import NetworkManager, NetworkAdapter, NetworkState


@click.group()
def network():
    """Manage network adapters for the airplane mode trick."""
    pass


def display_adapters(console: Console, adapters: list[NetworkAdapter]) -> None:
    """Display adapters in a nice table format (CLI layer)."""
    table = Table(title="Network Adapters")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Type", style="blue")
    table.add_column("Speed", style="magenta")

    for adapter in adapters:
        status = "✅ Enabled" if adapter.enabled else "❌ Disabled"
        speed = (
            f"{adapter.speed / 1000000:.0f} Mbps"
            if adapter.speed is not None
            else "Unknown"
        )
        table.add_row(adapter.id, adapter.name, status, adapter.adapter_type, speed)

    console.print(table)


def find_adapter(adapters: list[NetworkAdapter], query: str) -> NetworkAdapter | None:
    """Find an adapter by ID or name with fuzzy matching (CLI layer)."""
    # Try exact ID match first
    for adapter in adapters:
        if adapter.id == query:
            return adapter

    # Try exact name match
    for adapter in adapters:
        if adapter.name.lower() == query.lower():
            return adapter

    # Try partial name matches
    partial_matches = []
    query_lower = query.lower()
    for adapter in adapters:
        if query_lower in adapter.name.lower():
            partial_matches.append(adapter)

    # If we have exactly one partial match, return it
    if len(partial_matches) == 1:
        return partial_matches[0]

    return None


def select_adapters(console: Console, network_manager: NetworkManager) -> list[str]:
    """Let user select which adapters to toggle (CLI layer)."""
    adapters = network_manager.get_adapters()
    display_adapters(console, adapters)

    selected_ids: list[str] = []
    while True:
        query = Prompt.ask(
            "\nEnter adapter ID or name (or 'done' to finish)", default="done"
        )

        if query.lower() == "done":
            break

        # Try to find the adapter
        adapter = find_adapter(adapters, query)
        if not adapter:
            console.print(f"[red]No adapter found matching: {query}[/red]")
            continue

        if adapter.id in selected_ids:
            console.print(f"[yellow]Adapter {adapter.name} already selected[/yellow]")
            continue

        selected_ids.append(adapter.id)
        console.print(f"[green]Selected adapter: {adapter.name}[/green]")

    return selected_ids


@network.command()
@inject
def list(
    network_manager: NetworkManager = Provide[Container.network_manager],
):
    """List all network adapters."""
    if not platform.system() == "Windows":
        logger.error("This command only works on Windows")
        sys.exit(1)

    console = Console()
    adapters = network_manager.get_adapters()
    display_adapters(console, adapters)


@network.command()
@click.argument("adapter", required=False)
@inject
def disable(
    adapter: str | None,
    network_manager: NetworkManager = Provide[Container.network_manager],
):
    """Disable selected network adapters.

    If ADAPTER is provided, it will try to find and disable that specific adapter.
    Otherwise, it will prompt you to select adapters interactively.
    """
    if not platform.system() == "Windows":
        logger.error("This command only works on Windows")
        sys.exit(1)

    console = Console()

    if adapter:
        # Single adapter mode
        adapters = network_manager.get_adapters()
        found_adapter = find_adapter(adapters, adapter)
        if not found_adapter:
            logger.error(f"No adapter found matching: {adapter}")
            sys.exit(1)
        if network_manager.toggle_adapter(found_adapter.id, NetworkState.OFFLINE):
            logger.info(f"Successfully disabled adapter: {found_adapter.name}")
        else:
            logger.error(f"Failed to disable adapter: {found_adapter.name}")
    else:
        # Interactive selection mode
        selected_ids = select_adapters(console, network_manager)

        if not selected_ids:
            logger.warning("No adapters selected")
            return

        if not Confirm.ask("\nAre you sure you want to disable these adapters?"):
            logger.info("Operation cancelled")
            return

        if network_manager.toggle_adapters(selected_ids, NetworkState.OFFLINE):
            logger.info("Successfully toggled adapters")
        else:
            logger.warning("Failed to toggle some adapters")


@network.command()
@click.argument("adapter", required=False)
@inject
def enable(
    adapter: str | None,
    network_manager: NetworkManager = Provide[Container.network_manager],
):
    """Enable selected network adapters.

    If ADAPTER is provided, it will try to find and enable that specific adapter.
    Otherwise, it will prompt you to select adapters interactively.
    """
    if not platform.system() == "Windows":
        logger.error("This command only works on Windows")
        sys.exit(1)

    console = Console()

    if adapter:
        # Single adapter mode
        adapters = network_manager.get_adapters()
        found_adapter = find_adapter(adapters, adapter)
        if not found_adapter:
            logger.error(f"No adapter found matching: {adapter}")
            sys.exit(1)
        if network_manager.toggle_adapter(found_adapter.id, NetworkState.ONLINE):
            logger.info(f"Successfully enabled adapter: {found_adapter.name}")
        else:
            logger.error(f"Failed to enable adapter: {found_adapter.name}")
    else:
        # Interactive selection mode
        selected_ids = select_adapters(console, network_manager)

        if not selected_ids:
            logger.warning("No adapters selected")
            return

        if not Confirm.ask("\nAre you sure you want to enable these adapters?"):
            logger.info("Operation cancelled")
            return

        if network_manager.toggle_adapters(selected_ids, NetworkState.ONLINE):
            logger.info("Successfully toggled adapters")
        else:
            logger.warning("Failed to toggle some adapters")
