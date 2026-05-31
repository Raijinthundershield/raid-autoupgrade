"""Store owning the counted-Target screenshot lifecycle.

A Session counts the Target offline, then the user navigates away to spend on
the Fodder online. Getting back to the Target afterwards is error-prone, so the
tool keeps a full-window screenshot of the Target captured at the start of the
Count as a visual anchor for relocating it.

This store is a deep module: a small interface over two files under AppData,
carrying the coupling invariant that the displayed picture and the persisted
fail count are always a matched pair. The staging slot holds the picture of the
Count currently running; commit atomically promotes it to the committed slot in
the same step that the fail count is persisted; discard drops only staging so a
cancelled or errored Count never orphans a new picture against an old number.
"""

from pathlib import Path


class CountTargetScreenshot:
    def __init__(self, directory: Path) -> None:
        self._dir = directory
        self._staging = directory / "staging.png"
        self._committed = directory / "committed.png"

    def stage(self, image_bytes: bytes) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._staging.write_bytes(image_bytes)

    def commit(self) -> None:
        self._staging.replace(self._committed)

    def discard(self) -> None:
        self._staging.unlink(missing_ok=True)

    def read(self) -> bytes | None:
        if self._staging.exists():
            return self._staging.read_bytes()
        if self._committed.exists():
            return self._committed.read_bytes()
        return None
