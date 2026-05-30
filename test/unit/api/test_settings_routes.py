"""Contract tests for GET /api/settings and PUT /api/settings."""

from fastapi.testclient import TestClient

from raid_autoupgrade.api.app import create_app
from raid_autoupgrade.api.deps import get_settings_service
from raid_autoupgrade.services.settings_service import Settings


class _SettingsServiceStub:
    def __init__(self, stored: Settings | None = None) -> None:
        self._settings = stored or Settings()

    def get_settings(self) -> Settings:
        return self._settings

    def save_settings(self, settings: Settings) -> None:
        self._settings = settings


def test_get_settings_returns_defaults_when_unset():
    app = create_app()
    app.dependency_overrides[get_settings_service] = lambda: _SettingsServiceStub()

    with TestClient(app) as client:
        response = client.get("/api/settings")

    assert response.status_code == 200
    body = response.json()
    assert body["selected_adapters"] == []
    assert body["last_count_result"] is None


def test_put_settings_persists_and_returns_updated_settings():
    stub = _SettingsServiceStub()
    app = create_app()
    app.dependency_overrides[get_settings_service] = lambda: stub

    payload = {
        "selected_adapters": ["2", "5"],
        "last_count_result": {"fail_count": 4, "stop_reason": "upgraded"},
    }
    with TestClient(app) as client:
        response = client.put("/api/settings", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["selected_adapters"] == ["2", "5"]
    assert body["last_count_result"] == {"fail_count": 4, "stop_reason": "upgraded"}
    # verify service actually stored it
    assert stub.get_settings().selected_adapters == ["2", "5"]
