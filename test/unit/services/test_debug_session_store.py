"""Unit tests for DebugSessionStore's filesystem-level guarantees.

The HTTP layer is covered in test/unit/api/test_debug_routes.py; here we pin
the behaviours that are awkward to exercise through URL routing — chiefly
recursive session discovery (capture nests sessions under
``{kind}/{kind}/...``, and spend deeper still) and the path-traversal guard.
"""

import json

from raid_autoupgrade.services.debug_session_store import DebugSessionStore


def _write_session(root, rel, frames, images=None):
    """Materialise a captured session at ``root/rel`` like DebugFrameLogger."""
    session_dir = root / rel
    session_dir.mkdir(parents=True)
    summary = {"session_name": session_dir.name, "frames": frames}
    (session_dir / "debug_summary.json").write_text(json.dumps(summary))
    for filename, data in (images or {}).items():
        (session_dir / filename).write_bytes(data)


def test_disabled_store_lists_nothing():
    assert DebugSessionStore(debug_root=None).list_sessions() == []


def test_discovers_sessions_nested_under_the_real_capture_layout(tmp_path):
    # Count captures land at debug/count/count/<timestamp>/ (the doubled dir is
    # how run_fn + count_workflow compose the path); spend nests deeper still.
    _write_session(tmp_path, "count/count/20260531_120000_000", frames=[{}, {}])
    _write_session(tmp_path, "spend/spend/upgrade_1/20260531_130000_000", frames=[{}])

    sessions = DebugSessionStore(debug_root=tmp_path).list_sessions()

    # Most-recent-first by capture timestamp, addressed by their path under root.
    assert [(s.kind, s.id, s.frame_count) for s in sessions] == [
        ("spend", "spend/spend/upgrade_1/20260531_130000_000", 1),
        ("count", "count/count/20260531_120000_000", 2),
    ]


def test_read_frames_by_session_id(tmp_path):
    _write_session(tmp_path, "count/count/s1", frames=[{"detected_state": "fail"}])
    store = DebugSessionStore(debug_root=tmp_path)

    assert store.read_frames("count/count/s1") == [{"detected_state": "fail"}]


def test_read_frames_unknown_session_is_none(tmp_path):
    assert (
        DebugSessionStore(debug_root=tmp_path).read_frames("count/count/ghost") is None
    )


def test_read_image_returns_bytes_for_a_real_frame_image(tmp_path):
    _write_session(tmp_path, "count/count/s1", frames=[], images={"roi.png": b"png"})
    store = DebugSessionStore(debug_root=tmp_path)

    assert store.read_image("count/count/s1", "roi.png") == b"png"


def test_read_image_rejects_session_id_escaping_root(tmp_path):
    (tmp_path / "secret.png").write_bytes(b"top-secret")
    store = DebugSessionStore(debug_root=tmp_path)

    assert store.read_image("..", "secret.png") is None


def test_read_image_rejects_filename_escaping_session_dir(tmp_path):
    _write_session(tmp_path, "count/count/s1", frames=[], images={"roi.png": b"ok"})
    (tmp_path / "count" / "count" / "sibling.png").write_bytes(b"not-a-frame")
    store = DebugSessionStore(debug_root=tmp_path)

    assert store.read_image("count/count/s1", "../sibling.png") is None
