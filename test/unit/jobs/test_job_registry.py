"""Contract tests for JobRegistry."""

import queue
import threading
import time


def _wait_for_done(registry, job_id, timeout: float = 2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = registry.get_job(job_id)
        if state and state.status == "done":
            return state
        time.sleep(0.01)
    raise TimeoutError("job did not complete in time")


# ---------------------------------------------------------------------------
# Behavior 1: idle → start_job returns job_id; state is RUNNING
# ---------------------------------------------------------------------------


def test_start_job_when_idle_returns_job_id_and_running_state():
    from raid_autoupgrade.jobs.registry import JobRegistry

    registry = JobRegistry()
    started = threading.Event()
    finish = threading.Event()

    def run_fn(q: queue.Queue, cancel_event: threading.Event):
        started.set()
        finish.wait()

    job_id = registry.start_job(run_fn)
    started.wait(timeout=2.0)

    assert isinstance(job_id, str) and job_id
    state = registry.get_job(job_id)
    assert state is not None
    assert state.status == "running"

    finish.set()


# ---------------------------------------------------------------------------
# Behavior 3: event queue ordering — run_fn events arrive before done, in order
# ---------------------------------------------------------------------------


def test_event_queue_ordering():
    from raid_autoupgrade.jobs.registry import JobRegistry

    registry = JobRegistry()

    def run_fn(q: queue.Queue, cancel_event: threading.Event) -> dict | None:
        q.put({"type": "log", "msg": "first"})
        q.put({"type": "progress", "fail_count": 3})
        return {"fail_count": 3, "stop_reason": "max_attempts"}

    job_id = registry.start_job(run_fn)
    _wait_for_done(registry, job_id)

    q = registry.get_queue(job_id)
    events = []
    while not q.empty():
        events.append(q.get_nowait())

    assert len(events) == 3
    assert events[0] == {"type": "log", "msg": "first"}
    assert events[1] == {"type": "progress", "fail_count": 3}
    assert events[2]["type"] == "done"
    assert events[2]["result"] == {"fail_count": 3, "stop_reason": "max_attempts"}


# ---------------------------------------------------------------------------
# Behavior 2: busy → start_job raises ConflictError
# ---------------------------------------------------------------------------


def test_start_job_when_busy_raises_conflict():
    from raid_autoupgrade.jobs.registry import ConflictError, JobRegistry

    registry = JobRegistry()
    finish = threading.Event()

    def run_fn(q: queue.Queue, cancel_event: threading.Event):
        finish.wait()

    registry.start_job(run_fn)

    import pytest

    with pytest.raises(ConflictError):
        registry.start_job(run_fn)

    finish.set()


# ---------------------------------------------------------------------------
# Behavior: cancel sets the job's threading.Event
# ---------------------------------------------------------------------------


def test_cancel_sets_the_jobs_cancel_event():
    from raid_autoupgrade.jobs.registry import JobRegistry

    registry = JobRegistry()
    started = threading.Event()
    received_event: list[threading.Event] = []

    def run_fn(q: queue.Queue, cancel_event: threading.Event):
        received_event.append(cancel_event)
        started.set()
        cancel_event.wait(timeout=2.0)

    job_id = registry.start_job(run_fn)
    started.wait(timeout=2.0)

    assert not received_event[0].is_set()
    registry.cancel(job_id)
    assert received_event[0].is_set()


# ---------------------------------------------------------------------------
# Behavior: cancel is a no-op for unknown / already-done job
# ---------------------------------------------------------------------------


def test_cancel_unknown_job_is_noop():
    from raid_autoupgrade.jobs.registry import JobRegistry

    registry = JobRegistry()
    registry.cancel("does-not-exist")  # must not raise


# ---------------------------------------------------------------------------
# Behavior: mid-job exception → error event in queue; job transitions to done
# ---------------------------------------------------------------------------


def test_run_fn_exception_puts_error_event_and_job_becomes_done():
    from raid_autoupgrade.jobs.registry import JobRegistry

    registry = JobRegistry()

    def bad_run_fn(q: queue.Queue, cancel_event: threading.Event) -> dict | None:
        q.put({"type": "log", "msg": "starting"})
        raise RuntimeError("disk full")

    job_id = registry.start_job(bad_run_fn)
    _wait_for_done(registry, job_id)

    q_out = registry.get_queue(job_id)
    events = []
    while not q_out.empty():
        events.append(q_out.get_nowait())

    assert len(events) == 2
    assert events[0] == {"type": "log", "msg": "starting"}
    assert events[1]["type"] == "error"
    assert events[1]["error"] == "RuntimeError"
    assert events[1]["message"] == "disk full"

    state = registry.get_job(job_id)
    assert state is not None
    assert state.status == "done"
