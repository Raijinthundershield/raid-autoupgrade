"""Contract tests for SettingsService."""

from autoraid.services.settings_service import Settings, SettingsService


class _CacheStub:
    def __init__(self, store: dict | None = None) -> None:
        self._store: dict = store or {}

    def get(self, key: str, default=None):
        return self._store.get(key, default)

    def set(self, key: str, value) -> None:
        self._store[key] = value


def test_get_settings_returns_defaults_when_unset():
    svc = SettingsService(cache=_CacheStub())
    settings = svc.get_settings()
    assert settings.selected_adapters == []
    assert settings.last_count_result is None


def test_save_then_get_returns_saved_settings():
    svc = SettingsService(cache=_CacheStub())
    saved = Settings(
        selected_adapters=["1", "3"],
        last_count_result={"fail_count": 7, "stop_reason": "max_attempts"},
    )
    svc.save_settings(saved)
    result = svc.get_settings()
    assert result.selected_adapters == ["1", "3"]
    assert result.last_count_result == {"fail_count": 7, "stop_reason": "max_attempts"}
