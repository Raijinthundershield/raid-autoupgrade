"""Contract tests for the debug-only Label-tab endpoints (GET /api/debug/*).

The endpoints surface the progress-bar samples a `--debug` Count/Spend session
writes to disk. They are gated on debug being enabled: without `--debug` the
data endpoints are absent (404) and only /api/debug/status answers.
"""

import json

from fastapi.testclient import TestClient

from raid_autoupgrade.api.app import create_app
from raid_autoupgrade.api.deps import get_debug_session_store
from raid_autoupgrade.services.debug_session_store import DebugSessionStore


def _client(store: DebugSessionStore) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_debug_session_store] = lambda: store
    return TestClient(app)


def _write_session(
    root, kind: str, name: str, frames: list[dict], images: dict[str, bytes]
) -> None:
    """Materialise a captured session on disk like DebugFrameLogger does."""
    session_dir = root / kind / name
    session_dir.mkdir(parents=True)
    summary = {"session_name": name, "total_frames": len(frames), "frames": frames}
    (session_dir / "debug_summary.json").write_text(json.dumps(summary))
    for filename, data in images.items():
        (session_dir / filename).write_bytes(data)


# ---------------------------------------------------------------------------
# Tracer bullet: GET /api/debug/status reflects whether debug is enabled
# ---------------------------------------------------------------------------


def test_status_enabled_when_debug_root_configured(tmp_path):
    with _client(DebugSessionStore(debug_root=tmp_path)) as client:
        response = client.get("/api/debug/status")

    assert response.status_code == 200
    assert response.json() == {"enabled": True}


def test_status_disabled_when_no_debug_root():
    with _client(DebugSessionStore(debug_root=None)) as client:
        response = client.get("/api/debug/status")

    assert response.status_code == 200
    assert response.json() == {"enabled": False}


# ---------------------------------------------------------------------------
# GET /api/debug/sessions lists count + spend sessions, most-recent-first,
# kind-tagged, with each session's frame count.
# ---------------------------------------------------------------------------


def test_sessions_lists_both_kinds_most_recent_first(tmp_path):
    _write_session(tmp_path, "count", "20260531_120000_000", frames=[{}, {}], images={})
    _write_session(tmp_path, "spend", "20260531_130000_000", frames=[{}], images={})

    with _client(DebugSessionStore(debug_root=tmp_path)) as client:
        response = client.get("/api/debug/sessions")

    assert response.status_code == 200
    assert response.json() == {
        "sessions": [
            {"kind": "spend", "name": "20260531_130000_000", "frame_count": 1},
            {"kind": "count", "name": "20260531_120000_000", "frame_count": 2},
        ]
    }


def test_sessions_empty_when_no_captures(tmp_path):
    with _client(DebugSessionStore(debug_root=tmp_path)) as client:
        response = client.get("/api/debug/sessions")

    assert response.status_code == 200
    assert response.json() == {"sessions": []}


def test_sessions_404_when_debug_disabled():
    with _client(DebugSessionStore(debug_root=None)) as client:
        response = client.get("/api/debug/sessions")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/debug/sessions/{kind}/{name}/frames returns each captured frame,
# including the detector's recorded state guess and its image filenames.
# ---------------------------------------------------------------------------


_FRAMES = [
    {
        "timestamp": "20260531_120000_000",
        "frame_number": 0,
        "detected_state": "standby",
        "fail_count": 0,
        "screenshot_file": "20260531_120000_000_standby_screenshot.png",
        "roi_file": "20260531_120000_000_standby_roi.png",
        "avg_color_bgr": [10.0, 11.0, 12.0],
    },
    {
        "timestamp": "20260531_120000_200",
        "frame_number": 1,
        "detected_state": "fail",
        "fail_count": 1,
        "screenshot_file": "20260531_120000_200_fail_screenshot.png",
        "roi_file": "20260531_120000_200_fail_roi.png",
        "avg_color_bgr": [30.0, 40.0, 150.0],
    },
]


def test_frames_returns_captured_frames_with_state_guess(tmp_path):
    _write_session(tmp_path, "count", "20260531_120000_000", frames=_FRAMES, images={})

    with _client(DebugSessionStore(debug_root=tmp_path)) as client:
        response = client.get("/api/debug/sessions/count/20260531_120000_000/frames")

    assert response.status_code == 200
    assert response.json() == {"frames": _FRAMES}


def test_frames_404_for_unknown_session(tmp_path):
    with _client(DebugSessionStore(debug_root=tmp_path)) as client:
        response = client.get("/api/debug/sessions/count/nope/frames")

    assert response.status_code == 404


def test_frames_404_when_debug_disabled():
    with _client(DebugSessionStore(debug_root=None)) as client:
        response = client.get("/api/debug/sessions/count/whatever/frames")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/debug/sessions/{kind}/{name}/images/{filename} serves a frame's
# ROI or screenshot PNG.
# ---------------------------------------------------------------------------


_PNG = b"\x89PNG\r\n\x1a\nfake-roi-bytes"


def test_image_serves_png_bytes(tmp_path):
    _write_session(
        tmp_path,
        "count",
        "20260531_120000_000",
        frames=[],
        images={"roi.png": _PNG},
    )

    with _client(DebugSessionStore(debug_root=tmp_path)) as client:
        response = client.get(
            "/api/debug/sessions/count/20260531_120000_000/images/roi.png"
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == _PNG


def test_image_404_for_missing_file(tmp_path):
    _write_session(tmp_path, "count", "20260531_120000_000", frames=[], images={})

    with _client(DebugSessionStore(debug_root=tmp_path)) as client:
        response = client.get(
            "/api/debug/sessions/count/20260531_120000_000/images/ghost.png"
        )

    assert response.status_code == 404


def test_image_404_when_debug_disabled():
    with _client(DebugSessionStore(debug_root=None)) as client:
        response = client.get("/api/debug/sessions/count/whatever/images/roi.png")

    assert response.status_code == 404
