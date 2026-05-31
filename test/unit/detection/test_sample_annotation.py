"""Unit tests for labelled-sample annotation IO and discovery."""

import cv2
import numpy as np

from raid_autoupgrade.detection.sample_annotation import (
    SampleAnnotation,
    derive_metadata,
    discover_labeled_samples,
    load_annotation,
    write_annotation,
)


def _write_sample(directory, name, label):
    """Write a {name}.png + {name}.json pair into directory."""
    cv2.imwrite(str(directory / f"{name}.png"), np.zeros((4, 4, 3), dtype=np.uint8))
    write_annotation(directory / f"{name}.json", SampleAnnotation(label=label))


def test_derive_metadata_computes_avg_bgr_and_hsv_mean():
    """derive_metadata returns the mean BGR and mean HSV of a solid image."""
    # Solid pure-blue image (BGR = 255, 0, 0).
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    image[:, :, 0] = 255

    meta = derive_metadata(image)

    assert meta["avg_bgr"] == [255.0, 0.0, 0.0]
    # Pure blue in OpenCV HSV: H=120, S=255, V=255.
    h, s, v = meta["hsv_mean"]
    assert round(h) == 120
    assert round(s) == 255
    assert round(v) == 255


def test_annotation_round_trips_through_json(tmp_path):
    """An annotation written to a sidecar loads back with every field preserved."""
    annotation = SampleAnnotation(
        label="fail",
        window_size=[1920, 1080],
        avg_bgr=[10.0, 20.0, 200.0],
        hsv_mean=[0.0, 240.0, 200.0],
        fill_fraction=0.42,
        source="count debug session 2026-05-31",
    )
    path = tmp_path / "fail.json"

    write_annotation(path, annotation)
    loaded = load_annotation(path)

    assert loaded == annotation


def test_annotation_defaults_metadata_to_none():
    """Only label is required; metadata fields default to None."""
    annotation = SampleAnnotation(label="standby")

    assert annotation.window_size is None
    assert annotation.avg_bgr is None
    assert annotation.fill_fraction is None
    assert annotation.source is None


def test_discover_labeled_samples_pairs_each_annotation_with_its_image(tmp_path):
    """discover_labeled_samples globs sidecars and pairs each with its PNG."""
    _write_sample(tmp_path, "fail", "fail")
    _write_sample(tmp_path, "standby", "standby")

    samples = discover_labeled_samples(tmp_path)

    by_name = {s.image_path.name: s for s in samples}
    assert set(by_name) == {"fail.png", "standby.png"}
    assert by_name["fail.png"].annotation.label == "fail"
    assert by_name["standby.png"].image_path == tmp_path / "standby.png"


def test_skip_labelled_sample_is_not_assertable(tmp_path):
    """A sample with label 'skip' is discovered but flagged non-assertable."""
    _write_sample(tmp_path, "ambiguous", "skip")
    _write_sample(tmp_path, "clear", "fail")

    samples = {s.image_path.name: s for s in discover_labeled_samples(tmp_path)}

    assert samples["ambiguous.png"].is_assertable is False
    assert samples["clear.png"].is_assertable is True
