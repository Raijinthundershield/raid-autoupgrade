"""Contract tests for the CountTargetScreenshot store.

Seam: Service layer owning the counted-Target screenshot lifecycle behind a
small interface (stage / commit / discard / read). Its platform dependency is
the filesystem, exercised directly via tmp_path.

Invariant under test: the staging slot holds the live capture; commit promotes
it atomically; discard drops only staging; read prefers staging over committed.
"""

from pathlib import Path

from raid_autoupgrade.services.count_target_screenshot import CountTargetScreenshot


def test_stage_then_commit_promotes_to_committed_and_clears_staging(tmp_path: Path):
    store = CountTargetScreenshot(directory=tmp_path)

    store.stage(b"target-pixels")
    store.commit()

    assert store.read() == b"target-pixels"
    assert not (tmp_path / "staging.png").exists()
    assert (tmp_path / "committed.png").exists()


def test_discard_drops_staging_and_leaves_committed_untouched(tmp_path: Path):
    store = CountTargetScreenshot(directory=tmp_path)
    store.stage(b"old-target")
    store.commit()  # committed = old-target

    store.stage(b"new-target")  # a fresh Count begins
    store.discard()  # ...but it is cancelled

    assert store.read() == b"old-target"
    assert not (tmp_path / "staging.png").exists()


def test_read_prefers_staging_when_both_exist(tmp_path: Path):
    store = CountTargetScreenshot(directory=tmp_path)
    store.stage(b"committed-target")
    store.commit()
    store.stage(b"live-target")  # a Count is running again

    # A running Count shows the piece being counted live, not the last one.
    assert store.read() == b"live-target"


def test_read_returns_committed_when_only_committed_exists(tmp_path: Path):
    store = CountTargetScreenshot(directory=tmp_path)
    store.stage(b"committed-target")
    store.commit()

    assert store.read() == b"committed-target"


def test_read_returns_none_when_neither_exists(tmp_path: Path):
    store = CountTargetScreenshot(directory=tmp_path)

    assert store.read() is None
