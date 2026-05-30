from dataclasses import dataclass, field

from diskcache import Cache

from raid_autoupgrade.services.network import AdapterId

_KEY = "settings"


@dataclass
class Settings:
    selected_adapters: list[AdapterId] = field(default_factory=list)
    last_count_result: dict | None = None


class SettingsService:
    def __init__(self, cache: Cache) -> None:
        self._cache = cache

    def get_settings(self) -> Settings:
        stored = self._cache.get(_KEY)
        if stored is None:
            return Settings()
        return stored

    def save_settings(self, settings: Settings) -> None:
        self._cache.set(_KEY, settings)
