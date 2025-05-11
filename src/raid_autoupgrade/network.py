#!/usr/bin/env python3
import warnings
import socket
from urllib import request
from urllib.error import URLError

import wmi
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

warnings.filterwarnings("ignore", category=SyntaxWarning, module="wmi")


class NetworkAdapter:
    def __init__(
        self,
        name: str,
        id: str,
        enabled: bool,
        mac: str,
        adapter_type: str,
        speed: str | None,
    ) -> None:
        self.name = name
        self.id = id
        self.enabled = enabled
        self.mac = mac
        self.adapter_type = adapter_type
        self.speed = int(speed) if speed and speed.isdigit() else None


class NetworkManager:
    def __init__(self) -> None:
        self.wmi_obj = wmi.WMI()
        self.console = Console()

    def check_network_access(self, timeout: float = 5.0) -> bool:
        """Check if there is internet connectivity.

        Args:
            timeout (float): Timeout in seconds for the connection test

        Returns:
            bool: True if internet is accessible, False otherwise
        """
        try:
            # Try to connect to a reliable host
            socket.create_connection(("8.8.8.8", 53), timeout=timeout)
            return True
        except OSError:
            try:
                # Fallback to HTTP request
                request.urlopen("http://www.google.com", timeout=timeout)
                return True
            except (URLError, TimeoutError):
                return False

    def get_adapters(self) -> list[NetworkAdapter]:
        """Get all physical network adapters"""
        adapters: list[NetworkAdapter] = []
        for adapter in self.wmi_obj.Win32_NetworkAdapter(PhysicalAdapter=True):
            adapters.append(
                NetworkAdapter(
                    name=adapter.Name,
                    id=adapter.DeviceID,
                    enabled=adapter.NetEnabled,
                    mac=adapter.MACAddress,
                    adapter_type=adapter.AdapterType,
                    speed=str(adapter.Speed) if adapter.Speed else None,
                )
            )
        return adapters

    def display_adapters(self, adapters: list[NetworkAdapter]) -> None:
        """Display adapters in a nice table format"""
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

        self.console.print(table)

    def find_adapter(
        self, adapters: list[NetworkAdapter], query: str
    ) -> NetworkAdapter | None:
        """Find an adapter by ID or name with fuzzy matching"""
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

    def select_adapters(self) -> list[str]:
        """Let user select which adapters to toggle"""
        adapters = self.get_adapters()
        self.display_adapters(adapters)

        selected_ids: list[str] = []
        while True:
            query = Prompt.ask(
                "\nEnter adapter ID or name (or 'done' to finish)", default="done"
            )

            if query.lower() == "done":
                break

            # Try to find the adapter
            adapter = self.find_adapter(adapters, query)
            if not adapter:
                self.console.print(f"[red]No adapter found matching: {query}[/red]")
                continue

            if adapter.id in selected_ids:
                self.console.print(
                    f"[yellow]Adapter {adapter.name} already selected[/yellow]"
                )
                continue

            selected_ids.append(adapter.id)
            self.console.print(f"[green]Selected adapter: {adapter.name}[/green]")

        return selected_ids

    def toggle_adapter(self, adapter_id: str, enable: bool) -> bool:
        """Toggle a specific adapter"""
        try:
            adapter = self.wmi_obj.Win32_NetworkAdapter(DeviceID=adapter_id)[0]
            if enable:
                adapter.Enable()
                logger.info(f"Enabled adapter: {adapter.Name}")
            else:
                adapter.Disable()
                logger.info(f"Disabled adapter: {adapter.Name}")
            return True
        except Exception as e:
            logger.error(f"Failed to toggle adapter {adapter_id}: {str(e)}")
            return False

    def toggle_adapters(self, adapter_ids: list[str], enable: bool) -> bool:
        success_count = 0
        for adapter_id in adapter_ids:
            if self.toggle_adapter(adapter_id, enable):
                success_count += 1
        return success_count > 0

    def toggle_selected_adapters(self, enable: bool) -> None:
        """Toggle selected adapters"""
        selected_ids = self.select_adapters()

        if not selected_ids:
            logger.warning("No adapters selected")
            return

        if not Confirm.ask(
            f"\nAre you sure you want to {'enable' if enable else 'disable'} these adapters?"
        ):
            logger.info("Operation cancelled")
            return

        if self.toggle_adapters(selected_ids, enable):
            logger.info("Successfully toggled adapters")
        else:
            logger.warning("Failed to toggle some adapters")
