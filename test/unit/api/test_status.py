"""Contract tests for GET /api/status.

Stubs satisfy WindowInteractionProtocol and NetworkManagerProtocol structurally;
the type checker validates conformance — no unittest.mock needed.
"""

import pytest
from fastapi.testclient import TestClient

from raid_autoupgrade.api.app import create_app
from raid_autoupgrade.api.deps import get_network_manager, get_window_service
from raid_autoupgrade.services.network import NetworkState


class _WindowStub:
    def __init__(self, *, detected: bool) -> None:
        self._detected = detected

    def window_exists(self, window_title: str) -> bool:
        return self._detected


class _NetworkStub:
    def __init__(self, *, online: bool) -> None:
        self._state = NetworkState.ONLINE if online else NetworkState.OFFLINE

    def check_network_access(self, timeout: float = 5.0) -> NetworkState:
        return self._state


@pytest.fixture()
def client_both_healthy():
    app = create_app()
    app.dependency_overrides[get_window_service] = lambda: _WindowStub(detected=True)
    app.dependency_overrides[get_network_manager] = lambda: _NetworkStub(online=True)
    with TestClient(app) as c:
        yield c


def test_status_both_healthy(client_both_healthy):
    response = client_both_healthy.get("/api/status")
    assert response.status_code == 200
    assert response.json() == {"raid_window_detected": True, "network_online": True}


def test_status_window_not_found():
    app = create_app()
    app.dependency_overrides[get_window_service] = lambda: _WindowStub(detected=False)
    app.dependency_overrides[get_network_manager] = lambda: _NetworkStub(online=True)
    with TestClient(app) as client:
        response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json() == {"raid_window_detected": False, "network_online": True}


def test_status_network_offline():
    app = create_app()
    app.dependency_overrides[get_window_service] = lambda: _WindowStub(detected=True)
    app.dependency_overrides[get_network_manager] = lambda: _NetworkStub(online=False)
    with TestClient(app) as client:
        response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json() == {"raid_window_detected": True, "network_online": False}
