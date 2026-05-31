"""Smoke tests for NetworkManager service."""

import sys
from unittest.mock import patch

import pytest

from raid_autoupgrade.exceptions import NetworkAdapterError
from raid_autoupgrade.services.network import (
    NetworkAdapter,
    NetworkManager,
    NetworkState,
)

# Patches `network.wmi`, which is None off Windows (pywin32 is win32-only).
pytestmark = [
    pytest.mark.windows,
    pytest.mark.skipif(
        sys.platform != "win32", reason="Windows-only: WMI/pywin32 APIs"
    ),
]


class _FakeWmiAdapter:
    """Stand-in for a WMI ``Win32_NetworkAdapter`` COM object.

    Exposes the attributes ``get_adapters`` reads and records ``Enable``/
    ``Disable`` calls so tests can assert which physical adapter was toggled.
    """

    def __init__(
        self,
        *,
        name,
        device_id,
        pnp_device_id,
        net_enabled=True,
        mac="00:11:22:33:44:55",
        adapter_type="Ethernet 802.3",
        speed="1000000000",
    ):
        self.Name = name
        self.DeviceID = device_id
        self.PNPDeviceID = pnp_device_id
        self.NetEnabled = net_enabled
        self.MACAddress = mac
        self.AdapterType = adapter_type
        self.Speed = speed
        self.enabled_calls = 0
        self.disabled_calls = 0

    def Enable(self):
        self.enabled_calls += 1

    def Disable(self):
        self.disabled_calls += 1


@pytest.fixture
def network_manager():
    """Create a NetworkManager instance for testing."""
    with patch("raid_autoupgrade.services.network.wmi.WMI"):
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


class TestGetAdapters:
    """Test get_adapters exposes the stable PNPDeviceID as the adapter identity."""

    def test_id_is_pnp_device_id(self, network_manager):
        """The exposed identity is the stable PNPDeviceID, not the enumeration DeviceID."""
        pnp = r"PCI\VEN_8086&DEV_1539&SUBSYS_00008086&REV_03\3&11583659&0&C8"
        fake = _FakeWmiAdapter(
            name="Intel Ethernet",
            device_id="3",
            pnp_device_id=pnp,
        )
        with patch.object(network_manager, "_get_wmi") as get_wmi:
            get_wmi.return_value.Win32_NetworkAdapter.return_value = [fake]

            adapters = network_manager.get_adapters()

        assert adapters[0].id == pnp
        # Name stays the human-readable label the Network panel renders.
        assert adapters[0].name == "Intel Ethernet"


class TestToggleAdapter:
    """Test toggle_adapter resolves its target by matching PNPDeviceID in Python."""

    def test_disables_adapter_matching_pnp_device_id(self, network_manager):
        """The adapter whose PNPDeviceID matches is the one disabled.

        The id carries backslashes, so resolution must match over the live list
        rather than issue a WQL query keyed on the value.
        """
        target_pnp = r"PCI\VEN_8086&DEV_1539\3&11583659&0&C8"
        target = _FakeWmiAdapter(
            name="Intel Ethernet", device_id="3", pnp_device_id=target_pnp
        )
        other = _FakeWmiAdapter(
            name="Wi-Fi", device_id="4", pnp_device_id=r"PCI\VEN_8086&DEV_0000\other"
        )
        with patch.object(network_manager, "_get_wmi") as get_wmi:
            win32 = get_wmi.return_value.Win32_NetworkAdapter
            win32.return_value = [other, target]

            result = network_manager.toggle_adapter(target_pnp, NetworkState.OFFLINE)

        assert result is True
        assert target.disabled_calls == 1
        assert other.disabled_calls == 0
        # Resolution enumerates physical adapters; it never keys a WQL query on
        # the backslash-bearing id.
        for call in win32.call_args_list:
            assert "DeviceID" not in call.kwargs
            assert "PNPDeviceID" not in call.kwargs


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
                # Act & Assert: Should raise NetworkAdapterError on timeout
                with pytest.raises(NetworkAdapterError):
                    network_manager.wait_for_network_state(
                        NetworkState.OFFLINE, timeout=5.0
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

    def test_toggle_adapters_all_unresolved_fails_closed(
        self, network_manager, mock_adapters
    ):
        """A saved selection that no longer resolves fails closed.

        Raises NetworkAdapterError before toggling anything, so Count cannot
        proceed online against a rotted selection.
        """
        stale_id = r"PCI\VEN_1969&DEV_E091\stale-selection"
        with patch.object(network_manager, "get_adapters", return_value=mock_adapters):
            with patch.object(network_manager, "toggle_adapter") as mock_toggle:
                with pytest.raises(NetworkAdapterError):
                    network_manager.toggle_adapters(
                        [stale_id], NetworkState.OFFLINE, wait=True
                    )

                mock_toggle.assert_not_called()
