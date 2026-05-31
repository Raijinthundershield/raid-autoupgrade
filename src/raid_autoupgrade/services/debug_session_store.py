"""Read access to the progress-bar samples a ``--debug`` session captures.

A debug Count/Spend run writes one timestamped session directory per monitor
run, each holding a ``debug_summary.json`` (the captured frames, including the
detector's recorded state guess) plus the ROI and screenshot PNGs. The exact
nesting varies — Count lands at ``{root}/count/count/{ts}/`` and Spend at
``{root}/spend/spend/upgrade_{n}/{ts}/`` — so sessions are discovered by
recursively finding the summary files rather than assuming a fixed depth. A
session is then addressed by its path relative to the debug root.

This store is what the Label tab reviews captures through and exports
corrected labels back out of; it is disabled (no root) unless the GUI was
launched with ``--debug``.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import cv2

from raid_autoupgrade.detection.sample_annotation import (
    SampleAnnotation,
    derive_metadata,
    write_annotation,
)

_SUMMARY_FILE = "debug_summary.json"


@dataclass(frozen=True)
class DebugSession:
    """One captured session.

    ``id`` is the session directory's path relative to the debug root (posix
    style) and doubles as its address in the API. ``kind`` is the top-level
    group (``count`` | ``spend``); ``name`` is the leaf directory (the capture
    timestamp).
    """

    id: str
    kind: str
    name: str
    frame_count: int


class DebugSessionStore:
    """Discover and read captured debug sessions under a debug root.

    Args:
        debug_root: Root directory the capture side writes under, or ``None``
            when debug capture is disabled.
    """

    def __init__(self, debug_root: Path | None) -> None:
        self._root = debug_root.resolve() if debug_root is not None else None

    @property
    def enabled(self) -> bool:
        return self._root is not None

    def list_sessions(self) -> list[DebugSession]:
        """Discover captured sessions at any depth, most-recent-first.

        Session names are millisecond timestamps, so lexicographic descending
        order is chronological.
        """
        if self._root is None or not self._root.is_dir():
            return []

        sessions: list[DebugSession] = []
        for summary in self._root.rglob(_SUMMARY_FILE):
            session_dir = summary.parent
            rel = session_dir.relative_to(self._root).as_posix()
            frames = json.loads(summary.read_text()).get("frames", [])
            sessions.append(
                DebugSession(
                    id=rel,
                    kind=rel.split("/", 1)[0],
                    name=session_dir.name,
                    frame_count=len(frames),
                )
            )

        sessions.sort(key=lambda s: s.name, reverse=True)
        return sessions

    def read_frames(self, session_id: str) -> list[dict] | None:
        """Return a session's captured frames, or ``None`` if it doesn't exist."""
        session_dir = self._session_dir(session_id)
        if session_dir is None:
            return None
        summary = session_dir / _SUMMARY_FILE
        return json.loads(summary.read_text()).get("frames", [])

    def session_directory(self, session_id: str) -> str | None:
        """Return a session's absolute on-disk folder, or ``None`` if unknown.

        Exposed so the export flow can tell the reviewer exactly where the
        written samples landed.
        """
        session_dir = self._session_dir(session_id)
        return None if session_dir is None else str(session_dir)

    def read_image(self, session_id: str, filename: str) -> bytes | None:
        """Return a frame image's bytes, or ``None`` if absent.

        ``filename`` must name a file directly inside the session directory;
        anything that escapes it (a separator or ``..``) is rejected.
        """
        session_dir = self._session_dir(session_id)
        if session_dir is None:
            return None
        image_path = (session_dir / filename).resolve()
        if image_path.parent != session_dir or not image_path.is_file():
            return None
        return image_path.read_bytes()

    def export_labeled_samples(
        self, session_id: str, labels: list[dict]
    ) -> list[str] | None:
        """Write the Label tab's corrected labels back as fixture samples.

        ``labels`` carries one ``{"frame_number", "label"}`` entry per frame the
        reviewer chose to export. Each frame's ROI is copied to
        ``{label}_{w}x{h}_{n}.png`` (``w``×``h`` read from its screenshot) beside
        a :class:`SampleAnnotation` sidecar, ready to copy into
        ``test/fixtures/images/``. Returns the written PNG filenames, or ``None``
        when the session is unknown.
        """
        session_dir = self._session_dir(session_id)
        if session_dir is None:
            return None

        frames = self.read_frames(session_id) or []
        by_number = {f["frame_number"]: f for f in frames}

        written: list[str] = []
        for entry in labels:
            frame = by_number.get(entry["frame_number"])
            if frame is None:
                continue
            label = entry["label"]

            roi = cv2.imread(str(session_dir / frame["roi_file"]))
            shot = cv2.imread(str(session_dir / frame["screenshot_file"]))
            height, width = shot.shape[:2]

            n = 1
            while (session_dir / f"{label}_{width}x{height}_{n}.png").exists():
                n += 1
            stem = f"{label}_{width}x{height}_{n}"

            cv2.imwrite(str(session_dir / f"{stem}.png"), roi)
            meta = derive_metadata(roi)
            write_annotation(
                session_dir / f"{stem}.json",
                SampleAnnotation(
                    label=label,
                    window_size=[width, height],
                    avg_bgr=meta["avg_bgr"],
                    hsv_mean=meta["hsv_mean"],
                    fill_fraction=None,
                    source=(
                        f"{session_id}#frame{entry['frame_number']} "
                        f"guess={frame.get('detected_state')}"
                    ),
                ),
            )
            written.append(f"{stem}.png")
        return written

    def _session_dir(self, session_id: str) -> Path | None:
        """Resolve a session id to its directory, rejecting any id that escapes
        the root or doesn't point at a real captured session."""
        if self._root is None:
            return None
        session_dir = (self._root / session_id).resolve()
        if not session_dir.is_relative_to(self._root):
            return None
        if not (session_dir / _SUMMARY_FILE).is_file():
            return None
        return session_dir
