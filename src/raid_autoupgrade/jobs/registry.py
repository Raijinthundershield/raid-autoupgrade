import queue
import threading
import uuid
from dataclasses import dataclass
from typing import Literal
from collections.abc import Callable


class ConflictError(Exception):
    pass


@dataclass
class JobState:
    job_id: str
    status: Literal["running", "done"]
    result: dict | None = None


class JobRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active_job: str | None = None
        self._jobs: dict[str, JobState] = {}
        self._queues: dict[str, queue.Queue] = {}
        self._cancel_events: dict[str, threading.Event] = {}

    def start_job(
        self, run_fn: Callable[[queue.Queue, threading.Event], dict | None]
    ) -> str:
        with self._lock:
            if self._active_job is not None:
                raise ConflictError("a job is already running")
            job_id = str(uuid.uuid4())
            q: queue.Queue = queue.Queue()
            cancel_event = threading.Event()
            self._jobs[job_id] = JobState(job_id=job_id, status="running")
            self._queues[job_id] = q
            self._cancel_events[job_id] = cancel_event
            self._active_job = job_id

        def _worker() -> None:
            result: dict | None = None
            try:
                result = run_fn(q, cancel_event)
                q.put({"type": "done", "result": result})
            except Exception as exc:
                q.put(
                    {"type": "error", "error": type(exc).__name__, "message": str(exc)}
                )
            finally:
                with self._lock:
                    self._jobs[job_id] = JobState(
                        job_id=job_id, status="done", result=result
                    )
                    self._active_job = None
                    self._cancel_events.pop(job_id, None)

        threading.Thread(target=_worker, daemon=True).start()
        return job_id

    def cancel(self, job_id: str) -> None:
        with self._lock:
            event = self._cancel_events.get(job_id)
        if event is not None:
            event.set()

    def get_job(self, job_id: str) -> JobState | None:
        return self._jobs.get(job_id)

    def get_queue(self, job_id: str) -> queue.Queue | None:
        return self._queues.get(job_id)
