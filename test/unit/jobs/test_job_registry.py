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
    from autoraid.jobs.registry import JobRegistry

    registry = JobRegistry()
    started = threading.Event()
    finish = threading.Event()

    def run_fn(q: queue.Queue):
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
    from autoraid.jobs.registry import JobRegistry

    registry = JobRegistry()

    def run_fn(q: queue.Queue) -> dict | None:
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
    from autoraid.jobs.registry import ConflictError, JobRegistry

    registry = JobRegistry()
    finish = threading.Event()

    def run_fn(q: queue.Queue):
        finish.wait()

    registry.start_job(run_fn)

    import pytest

    with pytest.raises(ConflictError):
        registry.start_job(run_fn)

    finish.set()
