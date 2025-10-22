#!/usr/bin/env python3
import warnings
import socket
from dataclasses import dataclass
from urllib import request
from urllib.error import URLError

import wmi
from loguru import logger

warnings.filterwarnings("ignore", category=SyntaxWarning, module="wmi")


@dataclass
class NetworkAdapter:
    """Represents a network adapter with its properties."""

    name: str
    id: str
    enabled: bool
    mac: str
    adapter_type: str
    speed: str | None

    def __post_init__(self) -> None:
        """Convert speed from string to int after initialization."""
        if isinstance(self.speed, str) and self.speed.isdigit():
            self.speed = int(self.speed)
        elif isinstance(self.speed, str):
            self.speed = None


class NetworkManager:
    DEFAULT_TIMEOUT: float = 10.0
    CHECK_INTERVAL: float = 0.5

    def __init__(self) -> None:
        self.wmi_obj = wmi.WMI()

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
            logger.debug("Network status: ONLINE")
            return True
        except OSError:
            try:
                # Fallback to HTTP request
                request.urlopen("http://www.google.com", timeout=timeout)
                logger.debug("Network status: ONLINE")
                return True
            except (URLError, TimeoutError):
                logger.debug("Network status: OFFLINE")
                return False

    def wait_for_network_state(self, expected_online: bool, timeout: float) -> None:
        """Wait for network to reach expected state.

        Args:
            expected_online (bool): True to wait for online state, False for offline
            timeout (float): Maximum seconds to wait

        Raises:
            NetworkAdapterError: If timeout exceeded before reaching expected state
        """
        import time
        from autoraid.exceptions import NetworkAdapterError

        start_time = time.time()
        last_log_time = start_time

        state_name = "online" if expected_online else "offline"
        logger.info(f"Waiting for network to be {state_name} (timeout: {timeout}s)...")

        while True:
            elapsed = time.time() - start_time

            # Check for timeout
            if elapsed >= timeout:
                raise NetworkAdapterError(
                    f"Timeout waiting for network to be {state_name} after {timeout}s"
                )

            # Check current network state
            is_online = self.check_network_access()

            # Check if state matches expected
            if is_online == expected_online:
                logger.info(f"Network confirmed {state_name}")
                return

            # Log progress every 2 seconds
            if time.time() - last_log_time >= 2.0:
                logger.info(
                    f"Still waiting for network to be {state_name} "
                    f"({elapsed:.1f}s / {timeout}s)..."
                )
                last_log_time = time.time()

            # Wait before next check
            time.sleep(self.CHECK_INTERVAL)

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

    def toggle_adapters(
        self,
        adapter_ids: list[str],
        enable: bool,
        wait: bool = False,
        timeout: float | None = None,
    ) -> bool:
        """Toggle multiple network adapters with optional state waiting.

        Args:
            adapter_ids (list[str]): List of WMI device IDs to toggle
            enable (bool): True to enable adapters, False to disable
            wait (bool): If True, block until network state changes. Default: False
            timeout (float | None): Custom timeout in seconds. None uses default

        Returns:
            bool: True if at least one adapter toggled successfully, False otherwise

        Raises:
            NetworkAdapterError: If wait=True and timeout exceeded
        """
        logger.debug(
            f"toggle_adapters called with {len(adapter_ids)} adapters, "
            f"enable={enable}, wait={wait}, timeout={timeout}"
        )

        if not adapter_ids:
            logger.info("No adapters to toggle (empty list)")
            return True

        # Validate adapter IDs and filter out invalid ones (T004)
        valid_adapter_ids = []
        all_adapters = self.get_adapters()
        valid_ids_set = {adapter.id for adapter in all_adapters}

        for adapter_id in adapter_ids:
            if adapter_id in valid_ids_set:
                valid_adapter_ids.append(adapter_id)
            else:
                logger.warning(f"Invalid adapter ID: {adapter_id}")

        # If all IDs were invalid, return False
        if not valid_adapter_ids:
            logger.error("All adapter IDs were invalid")
            return False

        # Toggle each valid adapter
        success_count = 0
        for adapter_id in valid_adapter_ids:
            if self.toggle_adapter(adapter_id, enable):
                success_count += 1

        # If no adapters were successfully toggled, return False
        if success_count == 0:
            return False

        # If wait=True, wait for network state change (T003)
        if wait:
            timeout = self.DEFAULT_TIMEOUT if timeout is None else timeout

            expected_online = enable
            self.wait_for_network_state(expected_online, timeout)

            # Check for "internet still accessible" condition after disable
            if not enable and self.check_network_access():
                logger.warning(
                    "Internet still accessible via other network paths after disabling adapters"
                )

        return True
