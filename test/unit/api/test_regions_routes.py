"""Contract tests for GET /api/screenshot and PUT /api/regions."""

import numpy as np
from fastapi.testclient import TestClient

from autoraid.api.app import create_app


class _ScreenshotServiceStub:
    def __init__(self, image: np.ndarray):
        self._image = image

    def take_screenshot(self, window_title: str) -> np.ndarray:
        return self._image


class _WindowServiceStub:
    def __init__(self, size: tuple[int, int] = (1920, 1080)):
        self._size = size

    def window_exists(self, window_title: str) -> bool:
        return True

    def get_window_size(self, window_title: str) -> tuple[int, int]:
        return self._size


class _CacheServiceStub:
    def __init__(self):
        self.set_regions_calls: list[tuple] = []

    def set_regions(self, window_size: tuple[int, int], regions: dict) -> None:
        self.set_regions_calls.append((window_size, regions))

    def get_regions(self, window_size: tuple[int, int]) -> dict | None:
        return None

    def find_regions_any_size(self) -> tuple[tuple[int, int], dict] | None:
        return None


_SAMPLE_REGIONS = {
    "upgrade_bar": (10, 20, 300, 50),
    "upgrade_button": (500, 600, 100, 80),
}


class _CacheWithMatchingRegionsStub(_CacheServiceStub):
    def get_regions(self, window_size: tuple[int, int]) -> dict | None:
        return _SAMPLE_REGIONS

    def find_regions_any_size(self) -> tuple[tuple[int, int], dict] | None:
        return (1920, 1080), _SAMPLE_REGIONS


class _CacheWithStaleRegionsStub(_CacheServiceStub):
    """Has regions cached for a different window size."""

    def get_regions(self, window_size: tuple[int, int]) -> dict | None:
        return None

    def find_regions_any_size(self) -> tuple[tuple[int, int], dict] | None:
        return (1280, 720), _SAMPLE_REGIONS  # cached for a different size


# ---------------------------------------------------------------------------
# Behavior 5: GET /api/screenshot → 200 + PNG bytes
# ---------------------------------------------------------------------------


def test_get_screenshot_returns_png():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    app = create_app(
        screenshot_service=_ScreenshotServiceStub(image),
        window_service=_WindowServiceStub(),
    )

    with TestClient(app) as client:
        response = client.get("/api/screenshot")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content[:4] == b"\x89PNG"


# ---------------------------------------------------------------------------
# Behavior 6: GET /api/screenshot → 404 when window not found
# ---------------------------------------------------------------------------


class _MissingWindowScreenshotStub:
    def take_screenshot(self, window_title: str) -> np.ndarray:
        from autoraid.exceptions import WindowNotFoundException

        raise WindowNotFoundException("no window")


def test_get_screenshot_returns_404_when_window_missing():
    app = create_app(screenshot_service=_MissingWindowScreenshotStub())

    with TestClient(app) as client:
        response = client.get("/api/screenshot")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Behavior 7: PUT /api/regions valid body → 200, set_regions called
# ---------------------------------------------------------------------------


def test_put_regions_caches_regions_against_window_size():
    cache_stub = _CacheServiceStub()
    app = create_app(
        window_service=_WindowServiceStub(size=(1920, 1080)),
        cache_service=cache_stub,
    )

    with TestClient(app) as client:
        response = client.put(
            "/api/regions",
            json={
                "upgrade_bar": [10, 20, 300, 50],
                "upgrade_button": [500, 600, 100, 80],
            },
        )

    assert response.status_code == 200
    assert len(cache_stub.set_regions_calls) == 1
    window_size, regions = cache_stub.set_regions_calls[0]
    assert window_size == (1920, 1080)
    assert regions["upgrade_bar"] == (10, 20, 300, 50)
    assert regions["upgrade_button"] == (500, 600, 100, 80)


# ---------------------------------------------------------------------------
# Behavior 8: PUT /api/regions missing field → 422
# ---------------------------------------------------------------------------


def test_put_regions_missing_field_returns_422():
    app = create_app()

    with TestClient(app) as client:
        response = client.put("/api/regions", json={"upgrade_bar": [10, 20, 300, 50]})

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Behavior 9: PUT /api/regions wrong region length → 422
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Behavior 10: GET /api/regions → regions + no mismatch when cache matches
# ---------------------------------------------------------------------------


def test_get_regions_returns_regions_for_current_window_size():
    app = create_app(
        window_service=_WindowServiceStub(size=(1920, 1080)),
        cache_service=_CacheWithMatchingRegionsStub(),
    )

    with TestClient(app) as client:
        response = client.get("/api/regions")

    assert response.status_code == 200
    body = response.json()
    assert body["window_size_mismatch"] is False
    assert body["regions"]["upgrade_bar"] == [10, 20, 300, 50]
    assert body["regions"]["upgrade_button"] == [500, 600, 100, 80]


# ---------------------------------------------------------------------------
# Behavior 11: GET /api/regions → null regions when nothing is cached
# ---------------------------------------------------------------------------


def test_get_regions_returns_null_when_no_regions_cached():
    app = create_app(
        window_service=_WindowServiceStub(size=(1920, 1080)),
        cache_service=_CacheServiceStub(),
    )

    with TestClient(app) as client:
        response = client.get("/api/regions")

    assert response.status_code == 200
    body = response.json()
    assert body["regions"] is None
    assert body["window_size_mismatch"] is False


# ---------------------------------------------------------------------------
# Behavior 12: GET /api/regions → mismatch flag when cached for different size
# ---------------------------------------------------------------------------


def test_get_regions_flags_mismatch_when_cached_for_different_window_size():
    app = create_app(
        window_service=_WindowServiceStub(size=(1920, 1080)),
        cache_service=_CacheWithStaleRegionsStub(),
    )

    with TestClient(app) as client:
        response = client.get("/api/regions")

    assert response.status_code == 200
    body = response.json()
    assert body["regions"] is None
    assert body["window_size_mismatch"] is True


def test_put_regions_wrong_length_returns_422():
    app = create_app()

    with TestClient(app) as client:
        response = client.put(
            "/api/regions",
            json={
                "upgrade_bar": [10, 20, 300],  # only 3 values
                "upgrade_button": [500, 600, 100, 80],
            },
        )

    assert response.status_code == 422
