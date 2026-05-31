"""Contract tests for POST /api/workflows/count, GET /api/workflows/{job_id},
WS /ws/workflows/{job_id}, and POST /api/workflows/{job_id}/cancel."""

import queue

from fastapi.testclient import TestClient

from raid_autoupgrade.api.app import create_app
from raid_autoupgrade.api.deps import (
    get_count_runner,
    get_count_screenshot_store,
    get_job_registry,
)
from raid_autoupgrade.jobs.registry import ConflictError, JobState


class _ScreenshotStoreStub:
    def __init__(self, image_bytes: bytes | None):
        self._image_bytes = image_bytes

    def read(self) -> bytes | None:
        return self._image_bytes


class _RegistryStub:
    def __init__(self, job_id: str = "test-job-1"):
        self._job_id = job_id

    def start_job(self, run_fn) -> str:
        return self._job_id


class _ConflictRegistryStub:
    def start_job(self, run_fn) -> str:
        raise ConflictError("busy")


class _CancelRegistryStub:
    def __init__(self):
        self.cancelled: list[str] = []

    def cancel(self, job_id: str) -> None:
        self.cancelled.append(job_id)


# ---------------------------------------------------------------------------
# Behavior 4: POST → 200 with job_id
# ---------------------------------------------------------------------------


def test_post_count_returns_job_id():
    app = create_app()
    app.dependency_overrides[get_job_registry] = lambda: _RegistryStub(job_id="job-abc")
    app.dependency_overrides[get_count_runner] = lambda: lambda adapter_ids: (
        lambda q, cancel_event: None
    )

    with TestClient(app) as client:
        response = client.post("/api/workflows/count", json={"adapter_ids": None})

    assert response.status_code == 200
    assert response.json() == {"job_id": "job-abc"}


# ---------------------------------------------------------------------------
# Behavior 5: POST → 409 when a job is already running
# ---------------------------------------------------------------------------


def test_post_count_when_busy_returns_409():
    app = create_app()
    app.dependency_overrides[get_job_registry] = lambda: _ConflictRegistryStub()
    app.dependency_overrides[get_count_runner] = lambda: lambda adapter_ids: (
        lambda q, cancel_event: None
    )

    with TestClient(app) as client:
        response = client.post("/api/workflows/count", json={"adapter_ids": None})

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Behavior 6: GET → running state for known job
# ---------------------------------------------------------------------------


class _GetJobRegistryStub:
    def __init__(self, state: JobState | None):
        self._state = state

    def get_job(self, job_id: str) -> JobState | None:
        return self._state


def test_get_job_returns_running_state():
    app = create_app()
    state = JobState(job_id="job-1", status="running")
    app.dependency_overrides[get_job_registry] = lambda: _GetJobRegistryStub(
        state=state
    )

    with TestClient(app) as client:
        response = client.get("/api/workflows/job-1")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "job-1"
    assert body["status"] == "running"
    assert body["result"] is None


# ---------------------------------------------------------------------------
# Behavior 7: GET → 404 for unknown job
# ---------------------------------------------------------------------------


def test_get_job_unknown_returns_404():
    app = create_app()
    app.dependency_overrides[get_job_registry] = lambda: _GetJobRegistryStub(state=None)

    with TestClient(app) as client:
        response = client.get("/api/workflows/no-such-job")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Behavior 8 & 9: WS streams typed events in order; closes after done
# ---------------------------------------------------------------------------


class _WSRegistryStub:
    def __init__(self, job_id: str, q: queue.Queue):
        self._job_id = job_id
        self._q = q

    def get_queue(self, job_id: str) -> queue.Queue | None:
        return self._q if job_id == self._job_id else None


def test_websocket_streams_events_in_order_and_closes_after_done():
    q: queue.Queue = queue.Queue()
    q.put({"type": "progress", "fail_count": 0, "frames": 1, "state": "PROGRESS"})
    q.put({"type": "progress", "fail_count": 3, "frames": 10, "state": "FAIL"})
    q.put({"type": "done", "result": {"fail_count": 3, "stop_reason": "max_attempts"}})

    # The WS route reads the registry from app.state (a Request-typed
    # dependency cannot be satisfied in a websocket route), so inject the stub
    # the same way production wires it — via create_app — not dependency_overrides.
    app = create_app(job_registry=_WSRegistryStub("job-ws", q))

    with TestClient(app) as client:
        with client.websocket_connect("/ws/workflows/job-ws") as ws:
            e1 = ws.receive_json()
            e2 = ws.receive_json()
            e3 = ws.receive_json()

    assert e1 == {"type": "progress", "fail_count": 0, "frames": 1, "state": "PROGRESS"}
    assert e2 == {"type": "progress", "fail_count": 3, "frames": 10, "state": "FAIL"}
    assert e3["type"] == "done"
    assert e3["result"]["fail_count"] == 3


# ---------------------------------------------------------------------------
# Behavior: POST /api/workflows/{job_id}/cancel → 204 (idempotent)
# ---------------------------------------------------------------------------


def test_cancel_job_returns_204():
    stub = _CancelRegistryStub()
    app = create_app()
    app.dependency_overrides[get_job_registry] = lambda: stub

    with TestClient(app) as client:
        response = client.post("/api/workflows/some-job-id/cancel")

    assert response.status_code == 204
    assert stub.cancelled == ["some-job-id"]


def test_cancel_unknown_job_also_returns_204():
    stub = _CancelRegistryStub()
    app = create_app()
    app.dependency_overrides[get_job_registry] = lambda: stub

    with TestClient(app) as client:
        response = client.post("/api/workflows/ghost-job/cancel")

    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Behavior: WS closes after error event
# ---------------------------------------------------------------------------


def test_websocket_closes_after_error_event():
    q: queue.Queue = queue.Queue()
    q.put({"type": "progress", "fail_count": 0, "frames": 1, "state": "PROGRESS"})
    q.put({"type": "error", "error": "RuntimeError", "message": "disk full"})

    app = create_app(job_registry=_WSRegistryStub("job-err", q))

    with TestClient(app) as client:
        with client.websocket_connect("/ws/workflows/job-err") as ws:
            e1 = ws.receive_json()
            e2 = ws.receive_json()

    assert e1["type"] == "progress"
    assert e2["type"] == "error"
    assert e2["error"] == "RuntimeError"
    assert e2["message"] == "disk full"


# ---------------------------------------------------------------------------
# Behavior: POST forwards adapter_ids to the runner factory (debug-frame
# capture is no longer a per-request flag; it's gated by the --debug CLI flag
# at the composition root).
# ---------------------------------------------------------------------------


class _CapturingRunnerStub:
    """Records the args the factory was called with."""

    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, adapter_ids):
        self.calls.append({"adapter_ids": adapter_ids})
        return lambda q, cancel_event: None


def test_post_count_forwards_adapter_ids_to_runner():
    stub = _CapturingRunnerStub()
    app = create_app()
    app.dependency_overrides[get_job_registry] = lambda: _RegistryStub()
    app.dependency_overrides[get_count_runner] = lambda: stub

    adapter_ids = [
        r"PCI\VEN_8086&DEV_1539\3&11583659&0&C8",
        r"PCI\VEN_10EC&DEV_8168\4&abcd1234&0&00E0",
    ]
    with TestClient(app) as client:
        client.post("/api/workflows/count", json={"adapter_ids": adapter_ids})

    assert stub.calls[0]["adapter_ids"] == adapter_ids


# ---------------------------------------------------------------------------
# GET /api/last-count-screenshot → 200 + image/png when a picture exists
# ---------------------------------------------------------------------------


def test_get_last_count_screenshot_returns_png():
    app = create_app()
    app.dependency_overrides[get_count_screenshot_store] = lambda: _ScreenshotStoreStub(
        b"\x89PNG\r\n\x1a\nfake-png-bytes"
    )

    with TestClient(app) as client:
        response = client.get("/api/last-count-screenshot")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"\x89PNG\r\n\x1a\nfake-png-bytes"


# ---------------------------------------------------------------------------
# GET /api/last-count-screenshot → 404 when no picture has been kept yet
# ---------------------------------------------------------------------------


def test_get_last_count_screenshot_returns_404_when_empty():
    app = create_app()
    app.dependency_overrides[get_count_screenshot_store] = lambda: _ScreenshotStoreStub(
        None
    )

    with TestClient(app) as client:
        response = client.get("/api/last-count-screenshot")

    assert response.status_code == 404
