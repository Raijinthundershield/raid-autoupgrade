"""Annotations for labelled progress-bar-state samples.

Each sample image ``{name}.png`` is paired with a ``{name}.json`` sidecar
holding a :class:`SampleAnnotation` — its ground-truth label plus derived
metadata. The detector test discovers samples by globbing the sidecars; the
Label tab's export (#36) writes the same schema.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np

SKIP_LABEL = "skip"


@dataclass
class SampleAnnotation:
    """Ground-truth label and derived metadata for one sample image.

    Stored beside its image as a ``{name}.json`` sidecar. ``label`` is the
    recorded progress-bar state (or ``"skip"`` for samples that are
    deliberately not asserted). The remaining fields are metadata recorded
    ``where available``; legacy samples leave unknown fields as ``None``.
    """

    label: str
    window_size: list[int] | None = None
    avg_bgr: list[float] | None = None
    hsv_mean: list[float] | None = None
    fill_fraction: float | None = None
    source: str | None = None


@dataclass
class LabeledSample:
    """A sample image paired with its loaded annotation."""

    image_path: Path
    annotation: SampleAnnotation

    @property
    def is_assertable(self) -> bool:
        """Whether the detector test should assert this sample's label.

        ``skip`` samples are genuinely ambiguous (e.g. dim progress that is
        single-frame-indistinguishable from standby) and live in the dir for
        inspection without failing the suite.
        """
        return self.annotation.label != SKIP_LABEL


def discover_labeled_samples(directory: Path) -> list[LabeledSample]:
    """Glob ``*.json`` sidecars in a directory, pairing each with its PNG."""
    samples = []
    for sidecar_path in sorted(Path(directory).glob("*.json")):
        image_path = sidecar_path.with_suffix(".png")
        samples.append(LabeledSample(image_path, load_annotation(sidecar_path)))
    return samples


def write_annotation(path: Path, annotation: SampleAnnotation) -> None:
    """Write an annotation to ``path`` as an indented-JSON sidecar."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(annotation), f, indent=2)


def load_annotation(path: Path) -> SampleAnnotation:
    """Load an annotation from a ``{name}.json`` sidecar."""
    with open(path, encoding="utf-8") as f:
        return SampleAnnotation(**json.load(f))


def derive_metadata(image_bgr: np.ndarray) -> dict:
    """Compute the metadata derivable from a sample image alone.

    Returns the mean BGR and mean HSV of the image. ``fill_fraction`` is not
    derivable without the fill-detection algorithm (#37), so it is omitted here.
    """
    avg_bgr = list(cv2.mean(image_bgr)[:3])
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    hsv_mean = list(cv2.mean(hsv)[:3])
    return {"avg_bgr": avg_bgr, "hsv_mean": hsv_mean}
