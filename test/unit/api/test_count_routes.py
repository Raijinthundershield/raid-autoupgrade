"""Contract tests for POST /api/workflows/count, GET /api/workflows/{job_id},
and WS /ws/workflows/{job_id}."""

import queue

from fastapi.testclient import TestClient

from autoraid.api.app import create_app
from autoraid.api.deps import get_count_runner, get_job_registry
from autoraid.jobs.registry import ConflictError, JobState


class _RegistryStub:
    def __init__(self, job_id: str = "test-job-1"):
        self._job_id = job_id

    def start_job(self, run_fn) -> str:
        return self._job_id


class _ConflictRegistryStub:
    def start_job(self, run_fn) -> str:
        raise ConflictError("busy")


# ---------------------------------------------------------------------------
# Behavior 4: POST → 200 with job_id
# ---------------------------------------------------------------------------


def test_post_count_returns_job_id():
    app = create_app()
    app.dependency_overrides[get_job_registry] = lambda: _RegistryStub(job_id="job-abc")
    app.dependency_overrides[get_count_runner] = lambda: lambda adapter_ids: (
        lambda q: None
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
        lambda q: None
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
    q.put({"type": "log", "level": "INFO", "msg": "starting", "ts": 0})
    q.put({"type": "progress", "fail_count": 3, "frames": 10, "state": "FAIL"})
    q.put({"type": "done", "result": {"fail_count": 3, "stop_reason": "max_attempts"}})

    app = create_app()
    app.dependency_overrides[get_job_registry] = lambda: _WSRegistryStub("job-ws", q)

    with TestClient(app) as client:
        with client.websocket_connect("/ws/workflows/job-ws") as ws:
            e1 = ws.receive_json()
            e2 = ws.receive_json()
            e3 = ws.receive_json()

    assert e1 == {"type": "log", "level": "INFO", "msg": "starting", "ts": 0}
    assert e2 == {"type": "progress", "fail_count": 3, "frames": 10, "state": "FAIL"}
    assert e3["type"] == "done"
    assert e3["result"]["fail_count"] == 3
