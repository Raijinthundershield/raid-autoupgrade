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

    def test_noop_when_adapter_ids_none(self):
        """Verify NetworkContext is noop when adapter_ids=None."""
        mock_manager = Mock(spec=NetworkManager)

        with NetworkContext(mock_manager, adapter_ids=None, disable_network=True):
            pass

        # Verify no calls to toggle_adapters
        mock_manager.toggle_adapters.assert_not_called()

    def test_noop_when_adapter_ids_empty(self):
        """Verify NetworkContext is noop when adapter_ids is empty list."""
        mock_manager = Mock(spec=NetworkManager)

        with NetworkContext(mock_manager, adapter_ids=[], disable_network=True):
            pass

        # Verify no calls to toggle_adapters
        mock_manager.toggle_adapters.assert_not_called()

    def test_idempotency_via_was_disabled_tracking(self):
        """Verify NetworkContext only re-enables if it disabled."""
        mock_manager = Mock(spec=NetworkManager)

        # Test with disable_network=False (no disable, so no re-enable)
        with NetworkContext(mock_manager, adapter_ids=[1], disable_network=False):
            pass

        mock_manager.toggle_adapters.assert_not_called()

    def test_returns_self_from_enter(self):
        """Verify __enter__ returns self for context manager protocol."""
        mock_manager = Mock(spec=NetworkManager)

        context = NetworkContext(mock_manager, adapter_ids=[1], disable_network=True)
        result = context.__enter__()

        assert result is context

    def test_exit_returns_false(self):
        """Verify __exit__ returns False (doesn't suppress exceptions)."""
        mock_manager = Mock(spec=NetworkManager)

        context = NetworkContext(mock_manager, adapter_ids=[1], disable_network=True)
        context.__enter__()

        result = context.__exit__(None, None, None)

        assert result is False

    def test_multiple_adapter_ids(self):
        """Verify NetworkContext works with multiple adapter IDs."""
        mock_manager = Mock(spec=NetworkManager)

        with NetworkContext(mock_manager, adapter_ids=[1, 2, 3], disable_network=True):
            pass

        # Verify disable call
        disable_call = mock_manager.toggle_adapters.call_args_list[0]
        assert disable_call[0] == ([1, 2, 3], NetworkState.OFFLINE)

        # Verify enable call
        enable_call = mock_manager.toggle_adapters.call_args_list[1]
        assert enable_call[0] == ([1, 2, 3], NetworkState.ONLINE)

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
