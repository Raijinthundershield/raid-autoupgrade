"""Contract tests for GET /api/adapters."""

from fastapi.testclient import TestClient

from autoraid.api.app import create_app
from autoraid.api.deps import get_network_manager
from autoraid.services.network import NetworkAdapter


class _NetworkManagerStub:
    def __init__(self, adapters: list[NetworkAdapter]) -> None:
        self._adapters = adapters

    def get_adapters(self) -> list[NetworkAdapter]:
        return self._adapters


def test_get_adapters_returns_adapter_list():
    adapters = [
        NetworkAdapter(
            name="Wi-Fi",
            id="1",
            enabled=True,
            mac="AA:BB:CC:DD:EE:FF",
            adapter_type="Ethernet 802.3",
            speed=None,
        ),
        NetworkAdapter(
            name="Ethernet",
            id="2",
            enabled=False,
            mac="11:22:33:44:55:66",
            adapter_type="Ethernet 802.3",
            speed="1000000000",
        ),
    ]
    app = create_app()
    app.dependency_overrides[get_network_manager] = lambda: _NetworkManagerStub(
        adapters
    )

    with TestClient(app) as client:
        response = client.get("/api/adapters")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0] == {"id": "1", "name": "Wi-Fi", "enabled": True}
    assert body[1] == {"id": "2", "name": "Ethernet", "enabled": False}
