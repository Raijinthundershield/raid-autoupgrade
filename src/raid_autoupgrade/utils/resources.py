"""Frozen-aware resolution of bundled resource paths.

In a source checkout, bundled assets (e.g. ``frontend/dist``) live at the repo
root. In a PyInstaller onefile build they are unpacked under ``sys._MEIPASS``.
``resource_path`` returns the correct location for whichever layout is active,
so callers do not need to compute ``__file__``-relative paths that break once
frozen.
"""

import sys
from pathlib import Path


def resource_path(*relative_parts: str) -> Path:
    """Resolve a bundled resource to an absolute path.

    Args:
        relative_parts: Path components relative to the resource root
            (e.g. ``"frontend", "dist"``).

    Returns:
        A path under ``sys._MEIPASS`` when running as a PyInstaller onefile
        build, otherwise anchored at the repo root in a source checkout.
    """
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).resolve().parents[3]
    return base.joinpath(*relative_parts)
