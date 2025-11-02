"""Unit tests for NetworkContext."""

import pytest
from unittest.mock import Mock

from autoraid.utils.network_context import NetworkContext
from autoraid.services.network import NetworkManager, NetworkState


class TestNetworkContext:
    """Tests for NetworkContext class."""

    def test_disables_on_entry_enables_on_exit(self):
        """Verify NetworkContext disables on entry, enables on exit."""
        mock_manager = Mock(spec=NetworkManager)

        with NetworkContext(mock_manager, adapter_ids=[1, 2], disable_network=True):
            # Verify adapters disabled
            mock_manager.toggle_adapters.assert_called_once_with(
                [1, 2], NetworkState.OFFLINE, wait=True
            )
            mock_manager.reset_mock()

        # Verify adapters re-enabled on exit
        mock_manager.toggle_adapters.assert_called_once_with(
            [1, 2], NetworkState.ONLINE, wait=False
        )

    def test_reenables_on_exception(self):
        """Verify NetworkContext re-enables adapters even on exception."""
        mock_manager = Mock(spec=NetworkManager)

        try:
            with NetworkContext(mock_manager, adapter_ids=[1], disable_network=True):
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Verify adapters still re-enabled despite exception
        assert mock_manager.toggle_adapters.call_count == 2  # disable + enable

        # Verify second call was re-enable
        last_call = mock_manager.toggle_adapters.call_args_list[1]
        assert last_call[0] == ([1], NetworkState.ONLINE)

    def test_noop_when_disable_network_false(self):
        """Verify NetworkContext is noop when disable_network=False."""
        mock_manager = Mock(spec=NetworkManager)

        with NetworkContext(mock_manager, adapter_ids=[1], disable_network=False):
            pass

        # Verify no calls to toggle_adapters
        mock_manager.toggle_adapters.assert_not_called()

    def test_disable_waits_enable_does_not(self):
        """Verify disable waits but enable does not."""
        mock_manager = Mock(spec=NetworkManager)

        with NetworkContext(mock_manager, adapter_ids=[1], disable_network=True):
            pass

        # Verify disable call has wait=True
        disable_call = mock_manager.toggle_adapters.call_args_list[0]
        assert disable_call[1]["wait"] is True

        # Verify enable call has wait=False
        enable_call = mock_manager.toggle_adapters.call_args_list[1]
        assert enable_call[1]["wait"] is False

    def test_exception_not_suppressed(self):
        """Verify NetworkContext does not suppress exceptions."""
        mock_manager = Mock(spec=NetworkManager)

        with pytest.raises(ValueError, match="Test exception"):
            with NetworkContext(mock_manager, adapter_ids=[1], disable_network=True):
                raise ValueError("Test exception")

        # Still should have re-enabled
        assert mock_manager.toggle_adapters.call_count == 2
