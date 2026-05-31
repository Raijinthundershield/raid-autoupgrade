"""Unit tests for DebugSessionStore's filesystem-level guarantees.

The HTTP layer is covered in test/unit/api/test_debug_routes.py; here we pin
the behaviours that are awkward to exercise through URL routing — chiefly
recursive session discovery (capture nests sessions under
``{kind}/{kind}/...``, and spend deeper still) and the path-traversal guard.
"""

import json

import cv2
import numpy as np

from raid_autoupgrade.detection.sample_annotation import (
    discover_labeled_samples,
    load_annotation,
)
from raid_autoupgrade.services.debug_session_store import DebugSessionStore


def _write_session(root, rel, frames, images=None):
    """Materialise a captured session at ``root/rel`` like DebugFrameLogger."""
    session_dir = root / rel
    session_dir.mkdir(parents=True)
    summary = {"session_name": session_dir.name, "frames": frames}
    (session_dir / "debug_summary.json").write_text(json.dumps(summary))
    for filename, data in (images or {}).items():
        (session_dir / filename).write_bytes(data)


def _solid(height, width, bgr):
    """An h×w image filled with one BGR colour."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:, :] = bgr
    return img


def _capture(root, rel, frames):
    """Materialise a captured session with real ROI + screenshot images.

    ``frames`` is a list of dicts, each carrying ``frame_number``,
    ``detected_state``, a ``roi`` array and a ``shot`` array (the full-window
    screenshot whose dimensions stand in for the window size). Writes the PNGs
    and a ``debug_summary.json`` referencing them, like DebugFrameLogger would.
    """
    session_dir = root / rel
    session_dir.mkdir(parents=True)
    summary_frames = []
    for f in frames:
        n = f["frame_number"]
        roi_file = f"f{n}_roi.png"
        shot_file = f"f{n}_shot.png"
        cv2.imwrite(str(session_dir / roi_file), f["roi"])
        cv2.imwrite(str(session_dir / shot_file), f["shot"])
        summary_frames.append(
            {
                "frame_number": n,
                "detected_state": f["detected_state"],
                "roi_file": roi_file,
                "screenshot_file": shot_file,
            }
        )
    (session_dir / "debug_summary.json").write_text(
        json.dumps({"frames": summary_frames})
    )
    return session_dir


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


# ---------------------------------------------------------------------------
# export_labeled_samples writes the Label tab's corrected labels back into the
# session dir as {label}_{w}x{h}_{n}.png + a SampleAnnotation sidecar, ready to
# copy into test/fixtures/images/.
# ---------------------------------------------------------------------------


def test_export_writes_named_png_and_sidecar_for_a_labelled_frame(tmp_path):
    rel = "count/count/s1"
    _capture(
        tmp_path,
        rel,
        [
            {
                "frame_number": 0,
                "detected_state": "standby",
                "roi": _solid(4, 8, (0, 0, 200)),  # red ROI
                "shot": _solid(20, 30, (0, 0, 0)),  # 30×20 window
            }
        ],
    )
    store = DebugSessionStore(debug_root=tmp_path)

    written = store.export_labeled_samples(rel, [{"frame_number": 0, "label": "fail"}])

    # Named by the corrected label and the window size (from the screenshot).
    assert written == ["fail_30x20_1.png"]
    session_dir = tmp_path / rel
    assert (session_dir / "fail_30x20_1.png").is_file()
    assert load_annotation(session_dir / "fail_30x20_1.json").label == "fail"


def test_export_sidecar_carries_derived_metadata_and_provenance(tmp_path):
    rel = "count/count/s1"
    _capture(
        tmp_path,
        rel,
        [
            {
                "frame_number": 2,
                "detected_state": "standby",
                "roi": _solid(4, 8, (200, 0, 0)),  # solid blue ROI
                "shot": _solid(40, 60, (0, 0, 0)),  # 60×40 window
            }
        ],
    )
    store = DebugSessionStore(debug_root=tmp_path)

    store.export_labeled_samples(
        rel, [{"frame_number": 2, "label": "connection_error"}]
    )

    ann = load_annotation(tmp_path / rel / "connection_error_60x40_1.json")
    # Window size is the screenshot's [w, h].
    assert ann.window_size == [60, 40]
    # avg_bgr is the ROI's mean colour (solid blue → 200,0,0).
    assert ann.avg_bgr == [200.0, 0.0, 0.0]
    # hsv_mean is derived too (present, three channels).
    assert ann.hsv_mean is not None and len(ann.hsv_mean) == 3
    # fill_fraction stays null until #37 defines fill detection.
    assert ann.fill_fraction is None
    # source records where the sample came from: session, frame, detector guess.
    assert rel in ann.source
    assert "frame2" in ann.source
    assert "standby" in ann.source


def test_export_numbers_same_label_and_size_without_clobbering(tmp_path):
    rel = "count/count/s1"
    _capture(
        tmp_path,
        rel,
        [
            {
                "frame_number": i,
                "detected_state": "fail",
                "roi": _solid(4, 8, (0, 0, 200)),
                "shot": _solid(20, 30, (0, 0, 0)),
            }
            for i in range(2)
        ],
    )
    store = DebugSessionStore(debug_root=tmp_path)

    # First export takes _1; a second export of the other frame must not clobber.
    first = store.export_labeled_samples(rel, [{"frame_number": 0, "label": "fail"}])
    second = store.export_labeled_samples(rel, [{"frame_number": 1, "label": "fail"}])

    assert first == ["fail_30x20_1.png"]
    assert second == ["fail_30x20_2.png"]
    session_dir = tmp_path / rel
    assert (session_dir / "fail_30x20_1.png").is_file()
    assert (session_dir / "fail_30x20_2.png").is_file()


def test_export_unknown_session_returns_none(tmp_path):
    store = DebugSessionStore(debug_root=tmp_path)

    assert (
        store.export_labeled_samples(
            "count/count/ghost", [{"frame_number": 0, "label": "fail"}]
        )
        is None
    )


def test_exported_pairs_are_discovered_by_the_detector_globber(tmp_path):
    """The whole point: corrected labels become fixtures the detector test reads.

    Export, then copy the {png, json} pairs into a fixtures-style dir (the
    reviewer's manual step) and prove ``discover_labeled_samples`` picks them up
    with the right label — and that a ``skip`` is exported but flagged
    non-assertable.
    """
    rel = "count/count/s1"
    _capture(
        tmp_path,
        rel,
        [
            {
                "frame_number": 0,
                "detected_state": "unknown",
                "roi": _solid(4, 8, (0, 0, 200)),
                "shot": _solid(20, 30, (0, 0, 0)),
            },
            {
                "frame_number": 1,
                "detected_state": "standby",
                "roi": _solid(4, 8, (30, 30, 30)),
                "shot": _solid(20, 30, (0, 0, 0)),
            },
        ],
    )
    store = DebugSessionStore(debug_root=tmp_path)

    written = store.export_labeled_samples(
        rel,
        [
            {"frame_number": 0, "label": "fail"},
            {"frame_number": 1, "label": "skip"},
        ],
    )

    # Copy the exported pairs into a clean fixtures dir, like the reviewer would.
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    session_dir = tmp_path / rel
    for png in written:
        stem = png[: -len(".png")]
        (fixtures / png).write_bytes((session_dir / png).read_bytes())
        (fixtures / f"{stem}.json").write_text(
            (session_dir / f"{stem}.json").read_text()
        )

    by_label = {s.annotation.label: s for s in discover_labeled_samples(fixtures)}
    assert by_label["fail"].is_assertable is True
    assert by_label["skip"].is_assertable is False
