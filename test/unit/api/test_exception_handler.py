"""Contract tests for the central exception handler."""

from fastapi.testclient import TestClient

from autoraid.api.app import create_app
from autoraid.api.deps import get_count_runner
from autoraid.exceptions import WindowNotFoundException, WorkflowValidationError


def _runner_raising(exc_factory):
    """Return a count_runner dependency override whose factory raises exc_factory()."""

    def make_runner():
        def factory(adapter_ids, debug=False, log_debug=False):
            raise exc_factory()

        return factory

    return make_runner


# ---------------------------------------------------------------------------
# Behavior: WindowNotFoundException → 409 with error envelope
# ---------------------------------------------------------------------------


def test_window_not_found_returns_409_with_envelope():
    app = create_app()
    app.dependency_overrides[get_count_runner] = _runner_raising(
        lambda: WindowNotFoundException("Raid window not found.")
    )

    with TestClient(app) as client:
        response = client.post("/api/workflows/count", json={})

    assert response.status_code == 409
    body = response.json()
    assert body["error"] == "WindowNotFoundException"
    assert "Raid window not found" in body["message"]
    assert body["detail"] is None


# ---------------------------------------------------------------------------
# Behavior: WorkflowValidationError → 422 with error envelope
# ---------------------------------------------------------------------------


def test_workflow_validation_error_returns_422_with_envelope():
    app = create_app()
    app.dependency_overrides[get_count_runner] = _runner_raising(
        lambda: WorkflowValidationError("adapter required")
    )

    with TestClient(app) as client:
        response = client.post("/api/workflows/count", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "WorkflowValidationError"
    assert body["detail"] is None


# ---------------------------------------------------------------------------
# Behavior: unexpected exception → 500 with generic message (no detail leaked)
# ---------------------------------------------------------------------------


def test_unexpected_exception_returns_500_with_generic_message():
    app = create_app()
    app.dependency_overrides[get_count_runner] = _runner_raising(
        lambda: RuntimeError("secrets in error message")
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/workflows/count", json={})

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "InternalServerError"
    assert "secrets" not in body["message"]
    assert body["detail"] is None
