"""Contract tests for the debug-only Label-tab endpoints (GET /api/debug/*).

The endpoints surface the progress-bar samples a `--debug` Count/Spend session
writes to disk. They are gated on debug being enabled: without `--debug` the
data endpoints are absent (404) and only /api/debug/status answers. A session
is addressed by its id — its path relative to the debug root — which travels as
a query parameter because it bears slashes.
"""

import json

import cv2
import numpy as np
from fastapi.testclient import TestClient

from raid_autoupgrade.api.app import create_app
from raid_autoupgrade.api.deps import get_debug_session_store
from raid_autoupgrade.services.debug_session_store import DebugSessionStore


def _client(store: DebugSessionStore) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_debug_session_store] = lambda: store
    return TestClient(app)


def _write_session(root, rel, frames, images=None) -> None:
    """Materialise a captured session at ``root/rel`` like DebugFrameLogger."""
    session_dir = root / rel
    session_dir.mkdir(parents=True)
    summary = {"session_name": session_dir.name, "frames": frames}
    (session_dir / "debug_summary.json").write_text(json.dumps(summary))
    for filename, data in (images or {}).items():
        (session_dir / filename).write_bytes(data)


def _write_capture(root, rel, *, detected_state="standby", win=(30, 20)):
    """Materialise a one-frame session with real ROI + screenshot PNGs.

    ``win`` is the (width, height) the screenshot stands in for. Returns the
    session id ``rel``.
    """
    session_dir = root / rel
    session_dir.mkdir(parents=True)
    w, h = win
    cv2.imwrite(str(session_dir / "roi.png"), np.full((4, 8, 3), 200, dtype=np.uint8))
    cv2.imwrite(str(session_dir / "shot.png"), np.zeros((h, w, 3), dtype=np.uint8))
    frames = [
        {
            "frame_number": 0,
            "detected_state": detected_state,
            "roi_file": "roi.png",
            "screenshot_file": "shot.png",
        }
    ]
    (session_dir / "debug_summary.json").write_text(json.dumps({"frames": frames}))
    return rel


# ---------------------------------------------------------------------------
# GET /api/debug/status reflects whether debug is enabled
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
# kind-tagged, addressed by id, with each session's frame count.
# ---------------------------------------------------------------------------


def test_sessions_lists_both_kinds_most_recent_first(tmp_path):
    _write_session(tmp_path, "count/20260531_120000_000", frames=[{}, {}])
    _write_session(tmp_path, "spend/upgrade_1/20260531_130000_000", frames=[{}])

    with _client(DebugSessionStore(debug_root=tmp_path)) as client:
        response = client.get("/api/debug/sessions")

    assert response.status_code == 200
    assert response.json() == {
        "sessions": [
            {
                "id": "spend/upgrade_1/20260531_130000_000",
                "kind": "spend",
                "name": "20260531_130000_000",
                "frame_count": 1,
            },
            {
                "id": "count/20260531_120000_000",
                "kind": "count",
                "name": "20260531_120000_000",
                "frame_count": 2,
            },
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
# GET /api/debug/frames?session=... returns each captured frame, including the
# detector's recorded state guess and its image filenames.
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
    _write_session(tmp_path, "count/20260531_120000_000", frames=_FRAMES)

    with _client(DebugSessionStore(debug_root=tmp_path)) as client:
        response = client.get(
            "/api/debug/frames", params={"session": "count/20260531_120000_000"}
        )

    assert response.status_code == 200
    assert response.json() == {"frames": _FRAMES}


def test_frames_404_for_unknown_session(tmp_path):
    with _client(DebugSessionStore(debug_root=tmp_path)) as client:
        response = client.get("/api/debug/frames", params={"session": "count/nope"})

    assert response.status_code == 404


def test_frames_404_when_debug_disabled():
    with _client(DebugSessionStore(debug_root=None)) as client:
        response = client.get("/api/debug/frames", params={"session": "count/x"})

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/debug/image?session=...&file=... serves a frame's ROI/screenshot PNG.
# ---------------------------------------------------------------------------


_PNG = b"\x89PNG\r\n\x1a\nfake-roi-bytes"


def test_image_serves_png_bytes(tmp_path):
    _write_session(
        tmp_path, "count/20260531_120000_000", frames=[], images={"roi.png": _PNG}
    )

    with _client(DebugSessionStore(debug_root=tmp_path)) as client:
        response = client.get(
            "/api/debug/image",
            params={"session": "count/20260531_120000_000", "file": "roi.png"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == _PNG


def test_image_404_for_missing_file(tmp_path):
    _write_session(tmp_path, "count/20260531_120000_000", frames=[])

    with _client(DebugSessionStore(debug_root=tmp_path)) as client:
        response = client.get(
            "/api/debug/image",
            params={"session": "count/20260531_120000_000", "file": "ghost.png"},
        )

    assert response.status_code == 404


def test_image_404_when_debug_disabled():
    with _client(DebugSessionStore(debug_root=None)) as client:
        response = client.get(
            "/api/debug/image", params={"session": "count/x", "file": "roi.png"}
        )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/debug/export writes the reviewer's corrected labels back into the
# session as fixture samples, returning the written filenames.
# ---------------------------------------------------------------------------


def test_export_writes_samples_and_returns_filenames(tmp_path):
    rel = _write_capture(tmp_path, "count/20260531_120000_000", win=(30, 20))

    with _client(DebugSessionStore(debug_root=tmp_path)) as client:
        response = client.post(
            "/api/debug/export",
            json={"session": rel, "labels": [{"frame_number": 0, "label": "fail"}]},
        )

    assert response.status_code == 200
    assert response.json() == {"exported": ["fail_30x20_1.png"]}
    assert (tmp_path / rel / "fail_30x20_1.png").is_file()


def test_export_404_for_unknown_session(tmp_path):
    with _client(DebugSessionStore(debug_root=tmp_path)) as client:
        response = client.post(
            "/api/debug/export",
            json={
                "session": "count/nope",
                "labels": [{"frame_number": 0, "label": "fail"}],
            },
        )

    assert response.status_code == 404


def test_export_404_when_debug_disabled():
    with _client(DebugSessionStore(debug_root=None)) as client:
        response = client.post(
            "/api/debug/export",
            json={"session": "count/x", "labels": []},
        )

    assert response.status_code == 404
