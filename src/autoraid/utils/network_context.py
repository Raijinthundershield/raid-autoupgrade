"""Network management context manager.

This module provides a context manager for automatic network adapter
management with guaranteed cleanup.
"""

from loguru import logger

from autoraid.services.network import NetworkManager, NetworkState


class NetworkContext:
    """Context manager for automatic network adapter management.

    Disables specified network adapters on entry, re-enables on exit.
    Ensures adapters are always re-enabled, even on exceptions.

    Example:
        with NetworkContext(manager, adapter_ids=[1, 2], disable_network=True):
            # Network adapters 1 and 2 are disabled
            do_offline_work()
        # Adapters automatically re-enabled
    """

    def __init__(
        self,
        network_manager: NetworkManager,
        adapter_ids: list[int] | None = None,
        disable_network: bool = False,
    ):
        """Initialize network context.

        Args:
            network_manager: NetworkManager instance
            adapter_ids: List of adapter IDs to disable/enable
            disable_network: Whether to actually disable network (if False, noop)
        """
        self._network_manager = network_manager
        self._adapter_ids = adapter_ids
        self._disable_network = disable_network
        self._was_disabled = False

    def __enter__(self) -> "NetworkContext":
        """Disable network adapters on entry (if configured)."""
        if self._disable_network and self._adapter_ids:
            logger.info(f"Disabling network adapters: {self._adapter_ids}")
            self._network_manager.toggle_adapters(
                self._adapter_ids,
                NetworkState.OFFLINE,
                wait=True,
            )
            self._was_disabled = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Re-enable network adapters on exit (if we disabled them)."""
        if self._was_disabled and self._adapter_ids:
            logger.info(f"Re-enabling network adapters: {self._adapter_ids}")
            self._network_manager.toggle_adapters(
                self._adapter_ids,
                NetworkState.ONLINE,
                wait=False,
            )
        # Don't suppress exceptions
        return False
