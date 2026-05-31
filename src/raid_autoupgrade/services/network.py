#!/usr/bin/env python3
import socket
import threading
import time
import warnings
from dataclasses import dataclass
from enum import StrEnum
from typing import NewType
from urllib import request
from urllib.error import URLError

from loguru import logger

from raid_autoupgrade.exceptions import NetworkAdapterError

# pywin32/WMI ship win32 wheels only. Guard the import so this module loads on
# Linux/WSL (for the cross-platform test subset); the methods that touch `wmi`
# only run on Windows, behind the `windows`-marked tests. `wmi`/`pythoncom`
# stay module attributes so they remain patchable in those tests on Windows.
try:
    import pythoncom
    import wmi

    # Known issue with wmi module emitting SyntaxWarning
    warnings.filterwarnings("ignore", category=SyntaxWarning, module="wmi")
except ImportError:  # non-Windows
    pythoncom = None  # type: ignore[assignment]
    wmi = None  # type: ignore[assignment]


class _ThreadLocalWMI:
    def __init__(self):
        pythoncom.CoInitialize()
        self.wmi_obj = wmi.WMI()
        self._com_initialized = True

    def __del__(self):
        if hasattr(self, "_com_initialized") and self._com_initialized:
            try:
                pythoncom.CoUninitialize()
                self._com_initialized = False
            except Exception:
                # Suppress errors during cleanup (thread may be shutting down)
                pass


AdapterId = NewType("AdapterId", str)
"""Opaque, stable network-adapter identity (the Windows PNPDeviceID).

Threaded across every layer that selects an adapter so signatures read as a
domain identity. The value may contain backslashes, so it is matched in Python
against the live adapter list — never used as an unescaped WQL query key — and
never rendered as a raw DOM id.
"""


class NetworkState(StrEnum):
    """Network state enum for adapter operations."""

    ONLINE = "online"
    OFFLINE = "offline"


@dataclass
class NetworkAdapter:
    """Represents a network adapter with its properties."""

    name: str
    id: AdapterId
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
        self._thread_local = threading.local()

    def _get_wmi(self):
        if not hasattr(self._thread_local, "wmi_wrapper"):
            self._thread_local.wmi_wrapper = _ThreadLocalWMI()
        return self._thread_local.wmi_wrapper.wmi_obj

    def check_network_access(self, timeout: float = 5.0) -> NetworkState:
        """Check if there is internet connectivity.

        Args:
            timeout (float): Timeout in seconds for the connection test

        Returns:
            NetworkState: ONLINE if internet is accessible, OFFLINE otherwise
        """
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=timeout)
            logger.debug("Network status: ONLINE")
            return NetworkState.ONLINE
        except OSError:
            try:
                # Fallback to HTTP request
                request.urlopen("http://www.google.com", timeout=timeout)
                logger.debug("Network status: ONLINE")
                return NetworkState.ONLINE
            except (URLError, TimeoutError):
                logger.debug("Network status: OFFLINE")
                return NetworkState.OFFLINE

    def wait_for_network_state(
        self, target_state: NetworkState, timeout: float
    ) -> None:
        """Wait for network to reach expected state.

        Args:
            target_state: Target network state (NetworkState.ONLINE or NetworkState.OFFLINE)
            timeout: Maximum seconds to wait

        Raises:
            NetworkAdapterError: If timeout exceeded before reaching expected state
        """

        start_time = time.time()
        last_log_time = start_time

        logger.info(
            f"Waiting for network to be {target_state.value} (timeout: {timeout}s)..."
        )

        while True:
            elapsed = time.time() - start_time

            if elapsed >= timeout:
                raise NetworkAdapterError(
                    f"Network did not go {target_state.value} within {timeout}s. "
                    "Another connection may still be active — disable it in the "
                    "Network panel."
                )

            current_state = self.check_network_access()

            if current_state == target_state:
                logger.info(f"Network confirmed {target_state.value}")
                return

            if time.time() - last_log_time >= 2.0:
                logger.info(
                    f"Still waiting for network to be {target_state.value} "
                    f"({elapsed:.1f}s / {timeout}s)..."
                )
                last_log_time = time.time()

            time.sleep(self.CHECK_INTERVAL)

    def get_adapters(self) -> list[NetworkAdapter]:
        """Get all physical network adapters"""
        wmi_obj = self._get_wmi()
        adapters: list[NetworkAdapter] = []
        for adapter in wmi_obj.Win32_NetworkAdapter(PhysicalAdapter=True):
            adapters.append(
                NetworkAdapter(
                    name=adapter.Name,
                    id=AdapterId(adapter.PNPDeviceID),
                    enabled=adapter.NetEnabled,
                    mac=adapter.MACAddress,
                    adapter_type=adapter.AdapterType,
                    speed=str(adapter.Speed) if adapter.Speed else None,
                )
            )
        return adapters

    def toggle_adapter(self, adapter_id: AdapterId, target_state: NetworkState) -> bool:
        try:
            wmi_obj = self._get_wmi()
            # Match the stable PNPDeviceID in Python over the live adapter list.
            # The value contains backslashes, so it must not be used as an
            # unescaped WQL query key.
            adapter = next(
                a
                for a in wmi_obj.Win32_NetworkAdapter(PhysicalAdapter=True)
                if a.PNPDeviceID == adapter_id
            )
            if target_state == NetworkState.ONLINE:
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
        adapter_ids: list[AdapterId],
        target_state: NetworkState,
        wait: bool = False,
        timeout: float | None = None,
    ) -> bool:
        """Toggle multiple network adapters with optional state waiting.

        Args:
            adapter_ids: List of adapter identities (PNPDeviceIDs) to toggle
            target_state: Target network state (NetworkState.ONLINE or NetworkState.OFFLINE)
            wait: If True, block until network state changes. Default: False
            timeout: Custom timeout in seconds. None uses default

        Returns:
            True if at least one adapter toggled successfully, False otherwise

        Raises:
            NetworkAdapterError: If wait=True and timeout exceeded
        """
        logger.debug(
            f"toggle_adapters called with {len(adapter_ids)} adapters, "
            f"target_state={target_state.value}, wait={wait}, timeout={timeout}"
        )

        if not adapter_ids:
            logger.info("No adapters to toggle (empty list)")
            return True

        # Resolve each selected identity against the live adapter list, dropping
        # any that no longer match (graceful degradation when only some rot).
        valid_adapter_ids = []
        all_adapters = self.get_adapters()
        valid_ids_set = {adapter.id for adapter in all_adapters}

        for adapter_id in adapter_ids:
            if adapter_id in valid_ids_set:
                valid_adapter_ids.append(adapter_id)
            else:
                logger.warning(
                    f"Invalid adapter ID: {adapter_id}. Available IDs: {all_adapters}"
                )

        # If all IDs were invalid
        if not valid_adapter_ids:
            raise NetworkAdapterError(
                "No usable network adapter: none is selected, or the selected "
                "one is no longer available. Pick an adapter in the Network panel."
            )

        # Toggle each valid adapter
        success_count = 0
        for adapter_id in valid_adapter_ids:
            if self.toggle_adapter(adapter_id, target_state):
                success_count += 1

        # If no adapters were successfully toggled, return False
        if success_count == 0:
            return False

        # If wait=True, wait for network state change (T003)
        if wait:
            timeout = self.DEFAULT_TIMEOUT if timeout is None else timeout

            self.wait_for_network_state(target_state, timeout)

            # Check for "internet still accessible" condition after disable
            if (
                target_state == NetworkState.OFFLINE
                and self.check_network_access() == NetworkState.ONLINE
            ):
                logger.warning(
                    "Internet still accessible via other network paths after disabling adapters"
                )

        return True
