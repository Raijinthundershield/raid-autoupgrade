"""Contract tests for make_count_runner and make_spend_runner.

Seam: each factory returns a (params) → run_fn callable.
Contract: params control how the workflow is constructed; results are returned as dicts.
"""

import queue
import threading
from pathlib import Path

from raid_autoupgrade.jobs.run_fn import make_count_runner, make_spend_runner


class _WorkflowStub:
    """Records constructor kwargs instead of running anything."""

    last_instance: "_WorkflowStub | None" = None

    def __init__(self, **kwargs):
        _WorkflowStub.last_instance = self
        self._kwargs = kwargs

    def validate(self) -> None:
        pass

    def run(self, cancel_event=None, on_progress=None):
        from raid_autoupgrade.orchestration.stop_conditions import StopReason
        from raid_autoupgrade.workflows.count_workflow import CountResult

        return CountResult(fail_count=0, stop_reason=StopReason.MAX_ATTEMPTS_REACHED)

    @property
    def debug_dir(self):
        return self._kwargs.get("debug_dir")


# ---------------------------------------------------------------------------
# Behavior: a debug_dir_root → CountWorkflow receives debug_dir under the root.
# The root is wired only when the GUI is launched with --debug.
# ---------------------------------------------------------------------------


def test_factory_with_debug_root_passes_debug_dir_to_workflow(tmp_path: Path):
    debug_root = tmp_path / "debug"
    factory = make_count_runner(
        cache_service=None,
        window_service=None,
        network_manager=None,
        screenshot_service=None,
        detector=None,
        debug_dir_root=debug_root,
        workflow_class=_WorkflowStub,
    )

    import queue
    import threading

    run_fn = factory(adapter_ids=None)
    run_fn(queue.Queue(), threading.Event())

    assert _WorkflowStub.last_instance is not None
    assert _WorkflowStub.last_instance.debug_dir == debug_root / "count"


# ---------------------------------------------------------------------------
# Behavior: no debug_dir_root → debug_dir=None (no --debug, the exe default)
# ---------------------------------------------------------------------------


def test_factory_without_debug_root_passes_no_debug_dir():
    factory = make_count_runner(
        cache_service=None,
        window_service=None,
        network_manager=None,
        screenshot_service=None,
        detector=None,
        debug_dir_root=None,
        workflow_class=_WorkflowStub,
    )

    import queue
    import threading

    run_fn = factory(adapter_ids=None)
    run_fn(queue.Queue(), threading.Event())

    assert _WorkflowStub.last_instance is not None
    assert _WorkflowStub.last_instance.debug_dir is None


# ---------------------------------------------------------------------------
# Behavior: run_fn pushes progress events onto the queue via on_progress callback
# ---------------------------------------------------------------------------


class _WorkflowWithProgress:
    """Stub that calls on_progress with a fake ProgressEvent when run."""

    def __init__(self, **kwargs):
        self._kwargs = kwargs

    def validate(self) -> None:
        pass

    def run(self, cancel_event=None, on_progress=None):
        from raid_autoupgrade.detection.progress_bar_detector import ProgressBarState
        from raid_autoupgrade.orchestration.stop_conditions import StopReason
        from raid_autoupgrade.orchestration.upgrade_orchestrator import ProgressEvent
        from raid_autoupgrade.workflows.count_workflow import CountResult

        if on_progress is not None:
            on_progress(
                ProgressEvent(fail_count=2, frames=10, state=ProgressBarState.FAIL)
            )
        return CountResult(fail_count=2, stop_reason=StopReason.MAX_ATTEMPTS_REACHED)


def test_run_fn_pushes_progress_events_onto_queue():
    import queue
    import threading

    factory = make_count_runner(
        cache_service=None,
        window_service=None,
        network_manager=None,
        screenshot_service=None,
        detector=None,
        workflow_class=_WorkflowWithProgress,
    )

    q = queue.Queue()
    run_fn = factory(adapter_ids=None)
    run_fn(q, threading.Event())

    events = []
    while not q.empty():
        events.append(q.get_nowait())

    progress_events = [e for e in events if e.get("type") == "progress"]
    assert len(progress_events) == 1

    ev = progress_events[0]
    assert ev["fail_count"] == 2
    assert ev["frames"] == 10
    assert ev["state"] == "fail"


# ===========================================================================
# make_spend_runner
# ===========================================================================


class _SpendWorkflowStub:
    """Records constructor kwargs; returns a canned SpendResult."""

    last_instance: "_SpendWorkflowStub | None" = None

    def __init__(self, **kwargs):
        _SpendWorkflowStub.last_instance = self
        self._kwargs = kwargs

    def validate(self) -> None:
        pass

    def run(self, cancel_event=None, on_progress=None):
        from raid_autoupgrade.orchestration.stop_conditions import StopReason
        from raid_autoupgrade.workflows.spend_workflow import SpendResult

        return SpendResult(
            upgrade_count=1,
            attempt_count=5,
            remaining_attempts=2,
            stop_reason=StopReason.UPGRADED,
        )

    @property
    def continue_upgrade(self):
        return self._kwargs.get("continue_upgrade")

    @property
    def max_upgrade_attempts(self):
        return self._kwargs.get("max_upgrade_attempts")

    @property
    def debug_dir(self):
        return self._kwargs.get("debug_dir")


# ---------------------------------------------------------------------------
# Behavior: factory → run_fn returns dict with spend result fields
# ---------------------------------------------------------------------------


def test_spend_runner_returns_result_dict():
    factory = make_spend_runner(
        cache_service=None,
        window_service=None,
        network_manager=None,
        screenshot_service=None,
        detector=None,
        workflow_class=_SpendWorkflowStub,
    )

    run_fn = factory(max_upgrade_attempts=7, continue_upgrade=False)
    result = run_fn(queue.Queue(), threading.Event())

    assert result == {
        "upgrade_count": 1,
        "attempt_count": 5,
        "remaining_attempts": 2,
        "stop_reason": "upgraded",
    }


# ---------------------------------------------------------------------------
# Behavior: spend run_fn serializes an enriched SpendProgress onto the queue
# as a progress event carrying the Spend outcome fields.
# ---------------------------------------------------------------------------


class _SpendWorkflowWithProgress:
    """Stub that emits one cumulative SpendProgress snapshot when run."""

    def __init__(self, **kwargs):
        pass

    def validate(self) -> None:
        pass

    def run(self, cancel_event=None, on_progress=None):
        from raid_autoupgrade.detection.progress_bar_detector import ProgressBarState
        from raid_autoupgrade.orchestration.stop_conditions import StopReason
        from raid_autoupgrade.workflows.spend_workflow import SpendProgress, SpendResult

        if on_progress is not None:
            on_progress(
                SpendProgress(
                    attempts_used=3,
                    remaining=4,
                    upgrades=1,
                    state=ProgressBarState.FAIL,
                )
            )
        return SpendResult(
            upgrade_count=1,
            attempt_count=3,
            remaining_attempts=4,
            stop_reason=StopReason.UPGRADED,
        )


def test_spend_runner_serializes_enriched_progress_onto_queue():
    factory = make_spend_runner(
        cache_service=None,
        window_service=None,
        network_manager=None,
        screenshot_service=None,
        detector=None,
        workflow_class=_SpendWorkflowWithProgress,
    )

    q = queue.Queue()
    run_fn = factory(max_upgrade_attempts=10, continue_upgrade=False)
    run_fn(q, threading.Event())

    events = []
    while not q.empty():
        events.append(q.get_nowait())

    progress = [e for e in events if e.get("type") == "progress"]
    assert len(progress) == 1
    assert progress[0] == {
        "type": "progress",
        "attempts_used": 3,
        "remaining": 4,
        "upgrades": 1,
        "state": "fail",
    }


# ---------------------------------------------------------------------------
# Behavior: a debug_dir_root → SpendWorkflow receives debug_dir under the root,
# mirroring make_count_runner. The root is wired only with --debug.
# ---------------------------------------------------------------------------


def test_spend_runner_with_debug_root_passes_debug_dir_to_workflow(tmp_path: Path):
    debug_root = tmp_path / "debug"
    factory = make_spend_runner(
        cache_service=None,
        window_service=None,
        network_manager=None,
        screenshot_service=None,
        detector=None,
        debug_dir_root=debug_root,
        workflow_class=_SpendWorkflowStub,
    )

    _SpendWorkflowStub.last_instance = None
    run_fn = factory(max_upgrade_attempts=5, continue_upgrade=False)
    run_fn(queue.Queue(), threading.Event())

    assert _SpendWorkflowStub.last_instance is not None
    assert _SpendWorkflowStub.last_instance.debug_dir == debug_root / "spend"


# ---------------------------------------------------------------------------
# Behavior: no debug_dir_root → debug_dir=None (no --debug, the exe default)
# ---------------------------------------------------------------------------


def test_spend_runner_without_debug_root_passes_no_debug_dir():
    factory = make_spend_runner(
        cache_service=None,
        window_service=None,
        network_manager=None,
        screenshot_service=None,
        detector=None,
        debug_dir_root=None,
        workflow_class=_SpendWorkflowStub,
    )

    _SpendWorkflowStub.last_instance = None
    run_fn = factory(max_upgrade_attempts=5, continue_upgrade=False)
    run_fn(queue.Queue(), threading.Event())

    assert _SpendWorkflowStub.last_instance is not None
    assert _SpendWorkflowStub.last_instance.debug_dir is None


# ---------------------------------------------------------------------------
# Behavior: continue_upgrade is forwarded to workflow constructor
# ---------------------------------------------------------------------------


def test_spend_runner_passes_continue_upgrade_to_workflow():
    factory = make_spend_runner(
        cache_service=None,
        window_service=None,
        network_manager=None,
        screenshot_service=None,
        detector=None,
        workflow_class=_SpendWorkflowStub,
    )

    _SpendWorkflowStub.last_instance = None
    run_fn = factory(max_upgrade_attempts=3, continue_upgrade=True)
    run_fn(queue.Queue(), threading.Event())

    assert _SpendWorkflowStub.last_instance is not None
    assert _SpendWorkflowStub.last_instance.continue_upgrade is True


# ---------------------------------------------------------------------------
# Behavior: max_upgrade_attempts is forwarded to workflow constructor
# ---------------------------------------------------------------------------


def test_spend_runner_passes_max_attempts_to_workflow():
    factory = make_spend_runner(
        cache_service=None,
        window_service=None,
        network_manager=None,
        screenshot_service=None,
        detector=None,
        workflow_class=_SpendWorkflowStub,
    )

    _SpendWorkflowStub.last_instance = None
    run_fn = factory(max_upgrade_attempts=42, continue_upgrade=False)
    run_fn(queue.Queue(), threading.Event())

    assert _SpendWorkflowStub.last_instance is not None
    assert _SpendWorkflowStub.last_instance.max_upgrade_attempts == 42


# ===========================================================================
# make_count_runner — last_count_result persistence
# ===========================================================================


class _SettingsServiceStub:
    def __init__(self):
        self.saved: list = []
        self._current = None

    def get_settings(self):
        from raid_autoupgrade.services.settings_service import Settings

        return self._current if self._current is not None else Settings()

    def save_settings(self, settings) -> None:
        self._current = settings
        self.saved.append(settings)


# ---------------------------------------------------------------------------
# Behavior: after count run_fn completes, last_count_result is persisted
# ---------------------------------------------------------------------------


def test_count_runner_persists_result_to_settings_service():
    settings_stub = _SettingsServiceStub()
    factory = make_count_runner(
        cache_service=None,
        window_service=None,
        network_manager=None,
        screenshot_service=None,
        detector=None,
        workflow_class=_WorkflowStub,
        settings_service=settings_stub,
    )

    run_fn = factory(adapter_ids=None)
    run_fn(queue.Queue(), threading.Event())

    assert len(settings_stub.saved) == 1
    saved = settings_stub.saved[0]
    assert saved.last_count_result == {
        "fail_count": 0,
        "stop_reason": "max_attempts_reached",
    }


# ---------------------------------------------------------------------------
# Behavior: when no settings_service, count still completes normally
# ---------------------------------------------------------------------------


# ===========================================================================
# make_count_runner — counted-Target screenshot coupling
#
# Invariant: the screenshot commit and the last_count_result write are a matched
# pair. A finished Count stages then commits; a cancelled or errored Count
# discards its staging so the previous Target's picture and fail count survive.
# ===========================================================================


class _StoreStub:
    def __init__(self):
        self.staged: list[bytes] = []
        self.commits = 0
        self.discards = 0

    def stage(self, image_bytes: bytes) -> None:
        self.staged.append(image_bytes)

    def commit(self) -> None:
        self.commits += 1

    def discard(self) -> None:
        self.discards += 1


class _ScreenshotStub:
    def take_screenshot(self, window_title: str):
        import numpy as np

        return np.zeros((4, 4, 3), dtype=np.uint8)


class _CancelledWorkflowStub:
    """Returns a CountResult whose stop reason is MANUAL_STOP (user cancel)."""

    def __init__(self, **kwargs):
        pass

    def run(self, cancel_event=None, on_progress=None):
        from raid_autoupgrade.orchestration.stop_conditions import StopReason
        from raid_autoupgrade.workflows.count_workflow import CountResult

        return CountResult(fail_count=3, stop_reason=StopReason.MANUAL_STOP)


class _ErroringWorkflowStub:
    def __init__(self, **kwargs):
        pass

    def run(self, cancel_event=None, on_progress=None):
        raise RuntimeError("workflow blew up")


def test_count_runner_stages_at_start_and_commits_on_success():
    store = _StoreStub()
    factory = make_count_runner(
        cache_service=None,
        window_service=None,
        network_manager=None,
        screenshot_service=_ScreenshotStub(),
        detector=None,
        workflow_class=_WorkflowStub,
        screenshot_store=store,
    )

    run_fn = factory(adapter_ids=None)
    run_fn(queue.Queue(), threading.Event())

    assert len(store.staged) == 1  # captured at Count start
    assert store.commits == 1  # promoted on success
    assert store.discards == 0


def test_count_runner_discards_and_keeps_prior_result_on_cancel():
    store = _StoreStub()
    settings_stub = _SettingsServiceStub()
    factory = make_count_runner(
        cache_service=None,
        window_service=None,
        network_manager=None,
        screenshot_service=_ScreenshotStub(),
        detector=None,
        workflow_class=_CancelledWorkflowStub,
        settings_service=settings_stub,
        screenshot_store=store,
    )

    run_fn = factory(adapter_ids=None)
    run_fn(queue.Queue(), threading.Event())

    assert store.discards == 1
    assert store.commits == 0
    assert settings_stub.saved == []  # cancelled Count never overwrites the pair


def test_count_runner_discards_and_reraises_on_error():
    import pytest

    store = _StoreStub()
    factory = make_count_runner(
        cache_service=None,
        window_service=None,
        network_manager=None,
        screenshot_service=_ScreenshotStub(),
        detector=None,
        workflow_class=_ErroringWorkflowStub,
        screenshot_store=store,
    )

    run_fn = factory(adapter_ids=None)
    with pytest.raises(RuntimeError):
        run_fn(queue.Queue(), threading.Event())

    assert store.discards == 1
    assert store.commits == 0


def test_count_runner_without_settings_service_still_completes():
    factory = make_count_runner(
        cache_service=None,
        window_service=None,
        network_manager=None,
        screenshot_service=None,
        detector=None,
        workflow_class=_WorkflowStub,
        settings_service=None,
    )

    run_fn = factory(adapter_ids=None)
    result = run_fn(queue.Queue(), threading.Event())

    assert result["fail_count"] == 0
