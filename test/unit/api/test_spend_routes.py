"""Contract tests for POST /api/workflows/spend."""

from fastapi.testclient import TestClient

from autoraid.api.app import create_app
from autoraid.api.deps import get_job_registry, get_spend_runner
from autoraid.jobs.registry import ConflictError


class _RegistryStub:
    def __init__(self, job_id: str = "spend-job-1"):
        self._job_id = job_id

    def start_job(self, run_fn) -> str:
        return self._job_id


class _ConflictRegistryStub:
    def start_job(self, run_fn) -> str:
        raise ConflictError("busy")


class _CapturingRunnerStub:
    """Records args the factory was called with."""

    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, max_upgrade_attempts, continue_upgrade=False):
        self.calls.append(
            {
                "max_upgrade_attempts": max_upgrade_attempts,
                "continue_upgrade": continue_upgrade,
            }
        )
        return lambda q, cancel_event: None


# ---------------------------------------------------------------------------
# Behavior: POST → 200 with job_id
# ---------------------------------------------------------------------------


def test_post_spend_returns_job_id():
    app = create_app()
    app.dependency_overrides[get_job_registry] = lambda: _RegistryStub(
        job_id="spend-abc"
    )
    app.dependency_overrides[get_spend_runner] = (
        lambda: lambda max_upgrade_attempts, continue_upgrade=False: (
            lambda q, cancel_event: None
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/workflows/spend",
            json={"max_upgrade_attempts": 5, "continue_upgrade": False},
        )

    assert response.status_code == 200
    assert response.json() == {"job_id": "spend-abc"}


# ---------------------------------------------------------------------------
# Behavior: POST → 409 when a job is already running
# ---------------------------------------------------------------------------


def test_post_spend_when_busy_returns_409():
    app = create_app()
    app.dependency_overrides[get_job_registry] = lambda: _ConflictRegistryStub()
    app.dependency_overrides[get_spend_runner] = (
        lambda: lambda max_upgrade_attempts, continue_upgrade=False: (
            lambda q, cancel_event: None
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/workflows/spend",
            json={"max_upgrade_attempts": 5, "continue_upgrade": False},
        )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Behavior: continue_upgrade is forwarded to runner factory
# ---------------------------------------------------------------------------


def test_post_spend_with_continue_upgrade_passes_it_to_runner():
    stub = _CapturingRunnerStub()
    app = create_app()
    app.dependency_overrides[get_job_registry] = lambda: _RegistryStub()
    app.dependency_overrides[get_spend_runner] = lambda: stub

    with TestClient(app) as client:
        client.post(
            "/api/workflows/spend",
            json={"max_upgrade_attempts": 10, "continue_upgrade": True},
        )

    assert stub.calls[0]["continue_upgrade"] is True
    assert stub.calls[0]["max_upgrade_attempts"] == 10


# ---------------------------------------------------------------------------
# Behavior: continue_upgrade defaults to False
# ---------------------------------------------------------------------------


def test_post_spend_continue_upgrade_defaults_to_false():
    stub = _CapturingRunnerStub()
    app = create_app()
    app.dependency_overrides[get_job_registry] = lambda: _RegistryStub()
    app.dependency_overrides[get_spend_runner] = lambda: stub

    with TestClient(app) as client:
        client.post("/api/workflows/spend", json={"max_upgrade_attempts": 3})

    assert stub.calls[0]["continue_upgrade"] is False
