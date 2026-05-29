"""Contract tests for make_count_runner.

Seam: make_count_runner returns a factory; the factory builds a run_fn.
Contract: the debug/log_debug flags control how CountWorkflow is constructed.
"""

from pathlib import Path

from autoraid.jobs.run_fn import make_count_runner


class _WorkflowStub:
    """Records constructor kwargs instead of running anything."""

    last_instance: "_WorkflowStub | None" = None

    def __init__(self, **kwargs):
        _WorkflowStub.last_instance = self
        self._kwargs = kwargs

    def validate(self) -> None:
        pass

    def run(self, cancel_event=None):
        from autoraid.orchestration.stop_conditions import StopReason
        from autoraid.workflows.count_workflow import CountResult

        return CountResult(fail_count=0, stop_reason=StopReason.MAX_ATTEMPTS_REACHED)

    @property
    def debug_dir(self):
        return self._kwargs.get("debug_dir")


# ---------------------------------------------------------------------------
# Behavior: debug=True → CountWorkflow receives debug_dir under the root
# ---------------------------------------------------------------------------


def test_factory_with_debug_true_passes_debug_dir_to_workflow(tmp_path: Path):
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

    run_fn = factory(adapter_ids=None, debug=True, log_debug=False)
    run_fn(queue.Queue(), threading.Event())

    assert _WorkflowStub.last_instance is not None
    assert _WorkflowStub.last_instance.debug_dir == debug_root / "count"


# ---------------------------------------------------------------------------
# Behavior: debug=False → CountWorkflow receives debug_dir=None
# ---------------------------------------------------------------------------


def test_factory_with_debug_false_passes_no_debug_dir(tmp_path: Path):
    factory = make_count_runner(
        cache_service=None,
        window_service=None,
        network_manager=None,
        screenshot_service=None,
        detector=None,
        debug_dir_root=tmp_path / "debug",
        workflow_class=_WorkflowStub,
    )

    import queue
    import threading

    run_fn = factory(adapter_ids=None, debug=False, log_debug=False)
    run_fn(queue.Queue(), threading.Event())

    assert _WorkflowStub.last_instance is not None
    assert _WorkflowStub.last_instance.debug_dir is None


# ---------------------------------------------------------------------------
# Behavior: debug=True but no debug_dir_root → debug_dir=None (graceful)
# ---------------------------------------------------------------------------


def test_factory_with_debug_true_but_no_root_passes_no_debug_dir():
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

    run_fn = factory(adapter_ids=None, debug=True, log_debug=False)
    run_fn(queue.Queue(), threading.Event())

    assert _WorkflowStub.last_instance is not None
    assert _WorkflowStub.last_instance.debug_dir is None
