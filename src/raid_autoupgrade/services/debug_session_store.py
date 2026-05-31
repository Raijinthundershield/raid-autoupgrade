"""Read access to the progress-bar samples a ``--debug`` session captures.

A debug Count/Spend run writes one timestamped session directory per run under
``{debug_root}/{kind}/`` (kind = ``count`` | ``spend``), each holding a
``debug_summary.json`` (the captured frames, including the detector's recorded
state guess) plus the ROI and screenshot PNGs. This store is the read side the
Label tab reviews them through; it is disabled (no root) unless the GUI was
launched with ``--debug``.
"""

import json
from dataclasses import dataclass
from pathlib import Path

_KINDS = ("count", "spend")
_SUMMARY_FILE = "debug_summary.json"


@dataclass(frozen=True)
class DebugSession:
    """One captured session: its kind, directory name, and frame count."""

    kind: str
    name: str
    frame_count: int


class DebugSessionStore:
    """Enumerate and read captured debug sessions under a debug root.

    Args:
        debug_root: Root directory holding ``count/`` and ``spend/`` session
            dirs, or ``None`` when debug capture is disabled.
    """

    def __init__(self, debug_root: Path | None) -> None:
        self._root = debug_root

    @property
    def enabled(self) -> bool:
        return self._root is not None

    def list_sessions(self) -> list[DebugSession]:
        """Enumerate captured sessions across both kinds, most-recent-first.

        Session names are millisecond timestamps, so lexicographic descending
        order is chronological. A directory without a ``debug_summary.json`` is
        an incomplete/aborted capture and is skipped.
        """
        if self._root is None:
            return []

        sessions: list[DebugSession] = []
        for kind in _KINDS:
            kind_dir = self._root / kind
            if not kind_dir.is_dir():
                continue
            for session_dir in kind_dir.iterdir():
                summary = session_dir / _SUMMARY_FILE
                if not summary.is_file():
                    continue
                frames = json.loads(summary.read_text()).get("frames", [])
                sessions.append(DebugSession(kind, session_dir.name, len(frames)))

        sessions.sort(key=lambda s: s.name, reverse=True)
        return sessions

    def read_frames(self, kind: str, name: str) -> list[dict] | None:
        """Return a session's captured frames, or ``None`` if it doesn't exist."""
        session_dir = self._session_dir(kind, name)
        if session_dir is None:
            return None
        summary = session_dir / _SUMMARY_FILE
        if not summary.is_file():
            return None
        return json.loads(summary.read_text()).get("frames", [])

    def read_image(self, kind: str, name: str, filename: str) -> bytes | None:
        """Return a frame image's bytes, or ``None`` if absent.

        ``filename`` must name a file directly inside the session directory;
        anything that escapes it (a separator or ``..``) is rejected.
        """
        session_dir = self._session_dir(kind, name)
        if session_dir is None:
            return None
        image_path = (session_dir / filename).resolve()
        if image_path.parent != session_dir or not image_path.is_file():
            return None
        return image_path.read_bytes()

    def _session_dir(self, kind: str, name: str) -> Path | None:
        """Resolve a session directory, guarding against an unknown kind and
        any ``name`` that escapes the kind directory."""
        if self._root is None or kind not in _KINDS:
            return None
        kind_dir = (self._root / kind).resolve()
        session_dir = (kind_dir / name).resolve()
        if session_dir.parent != kind_dir or not session_dir.is_dir():
            return None
        return session_dir
