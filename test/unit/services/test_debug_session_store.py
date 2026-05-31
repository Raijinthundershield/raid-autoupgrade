"""Unit tests for DebugSessionStore's filesystem-level guarantees.

The HTTP layer is covered in test/unit/api/test_debug_routes.py; here we pin
the behaviours that are awkward to exercise through URL routing — chiefly the
path-traversal guard on session names and image filenames.
"""

import json

from raid_autoupgrade.services.debug_session_store import DebugSessionStore


def _write_session(root, kind, name, frames, images):
    session_dir = root / kind / name
    session_dir.mkdir(parents=True)
    summary = {"session_name": name, "total_frames": len(frames), "frames": frames}
    (session_dir / "debug_summary.json").write_text(json.dumps(summary))
    for filename, data in images.items():
        (session_dir / filename).write_bytes(data)


def test_disabled_store_lists_nothing():
    assert DebugSessionStore(debug_root=None).list_sessions() == []


def test_read_frames_rejects_unknown_kind(tmp_path):
    _write_session(tmp_path, "count", "s1", frames=[{}], images={})
    store = DebugSessionStore(debug_root=tmp_path)

    assert store.read_frames("evil", "s1") is None


def test_read_image_rejects_name_escaping_kind_dir(tmp_path):
    # A secret beside the kind dir must not be reachable via a ".." name.
    (tmp_path / "count").mkdir()
    (tmp_path / "secret.png").write_bytes(b"top-secret")
    store = DebugSessionStore(debug_root=tmp_path)

    assert store.read_image("count", "..", "secret.png") is None


def test_read_image_rejects_filename_escaping_session_dir(tmp_path):
    _write_session(tmp_path, "count", "s1", frames=[], images={"roi.png": b"ok"})
    # A sibling file in the kind dir, outside the session dir, must not be
    # reachable via a traversing filename.
    (tmp_path / "count" / "sibling.png").write_bytes(b"not-a-frame")
    store = DebugSessionStore(debug_root=tmp_path)

    assert store.read_image("count", "s1", "../sibling.png") is None


def test_read_image_returns_bytes_for_a_real_frame_image(tmp_path):
    _write_session(tmp_path, "count", "s1", frames=[], images={"roi.png": b"png-bytes"})
    store = DebugSessionStore(debug_root=tmp_path)

    assert store.read_image("count", "s1", "roi.png") == b"png-bytes"
