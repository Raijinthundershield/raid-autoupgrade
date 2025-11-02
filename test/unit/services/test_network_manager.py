"""Smoke tests for NetworkManager service."""

import pytest
from unittest.mock import patch

from autoraid.services.network import NetworkManager, NetworkAdapter, NetworkState
from autoraid.exceptions import NetworkAdapterError


@pytest.fixture
def network_manager():
    """Create a NetworkManager instance for testing."""
    with patch("autoraid.services.network.wmi.WMI"):
        manager = NetworkManager()
        return manager


@pytest.fixture
def mock_adapters():
    """Create mock network adapters for testing."""
    return [
        NetworkAdapter(
            name="Ethernet",
            id="0",
            enabled=True,
            mac="00:11:22:33:44:55",
            adapter_type="Ethernet",
            speed="1000000000",  # 1 Gbps
        ),
        NetworkAdapter(
            name="Wi-Fi",
            id="1",
            enabled=False,
            mac="AA:BB:CC:DD:EE:FF",
            adapter_type="WiFi",
            speed="100000000",  # 100 Mbps
        ),
    ]


class TestToggleAdaptersWithWait:
    """Test toggle_adapters with wait=True (blocking until state change)."""

    def test_toggle_adapters_with_wait_success(self, network_manager, mock_adapters):
        """Verify wait_for_network_state called when wait=True."""
        # Mock dependencies
        with patch.object(network_manager, "get_adapters", return_value=mock_adapters):
            with patch.object(network_manager, "toggle_adapter", return_value=True):
                with patch.object(
                    network_manager, "wait_for_network_state"
                ) as mock_wait:
                    with patch.object(
                        network_manager,
                        "check_network_access",
                        return_value=NetworkState.OFFLINE,
                    ):
                        # Act
                        result = network_manager.toggle_adapters(
                            ["0"], NetworkState.OFFLINE, wait=True
                        )

                        # Assert
                        assert result is True
                        # Check positional args (the method is called with positional args)
                        assert mock_wait.call_count == 1
                        call_args = mock_wait.call_args[0]
                        assert call_args[0] == NetworkState.OFFLINE  # target_state
                        assert call_args[1] == 10.0  # timeout (DEFAULT_TIMEOUT)


class TestWaitForNetworkState:
    """Test wait_for_network_state method behavior."""

    def test_wait_for_network_state_timeout(self, network_manager):
        """Verify NetworkAdapterError raised on timeout."""
        # Mock check_network_access to always return wrong state (online when expecting offline)
        with patch.object(
            network_manager, "check_network_access", return_value=NetworkState.ONLINE
        ):
            # Use a callable that simulates time passing to trigger timeout
            call_count = [0]

            def fake_time():
                result = (
                    call_count[0] * 10
                )  # 0, 10, 20, 30... (always exceeding timeout after first iteration)
                call_count[0] += 1
                return result

            with patch("time.time", fake_time):
                # Act & Assert: Should raise NetworkAdapterError
                with pytest.raises(NetworkAdapterError) as exc_info:
                    network_manager.wait_for_network_state(
                        NetworkState.OFFLINE, timeout=5.0
                    )

                assert "Timeout waiting for network to be offline after 5.0s" in str(
                    exc_info.value
                )


class TestInvalidAdapterHandling:
    """Test invalid adapter ID validation and warning logging."""

    def test_toggle_adapters_invalid_ids(self, network_manager, mock_adapters):
        """Verify graceful degradation with warning logs for invalid IDs."""
        # Mock get_adapters to return only adapters with IDs "0" and "1"
        with patch.object(network_manager, "get_adapters", return_value=mock_adapters):
            with patch.object(
                network_manager, "toggle_adapter", return_value=True
            ) as mock_toggle:
                # Act: Try to toggle mix of invalid and valid IDs
                result = network_manager.toggle_adapters(
                    ["invalid-id", "0", "999"], NetworkState.OFFLINE, wait=False
                )

                # Assert:
                # 1. Should return True (at least one valid adapter succeeded)
                assert result is True

                # 2. Should only toggle valid adapter "0"
                assert mock_toggle.call_count == 1
                mock_toggle.assert_called_with("0", NetworkState.OFFLINE)
