"""Factory that builds the count workflow run_fn for JobRegistry.start_job."""

import queue as _queue
import threading
from collections.abc import Callable
from pathlib import Path

from loguru import logger

from autoraid.workflows.count_workflow import CountWorkflow


def _make_log_sink(q: _queue.Queue) -> Callable:
    def sink(message) -> None:
        record = message.record
        q.put(
            {
                "type": "log",
                "level": record["level"].name,
                "msg": record["message"],
                "ts": record["time"].timestamp(),
            }
        )

    return sink


def make_count_runner(
    cache_service,
    window_service,
    network_manager,
    screenshot_service,
    detector,
    debug_dir_root: Path | None = None,
    workflow_class=CountWorkflow,
) -> Callable[
    [list[int] | None, bool, bool],
    Callable[[_queue.Queue, threading.Event], dict | None],
]:
    """Return a factory: (adapter_ids, debug, log_debug) → run_fn for JobRegistry.start_job."""

    def factory(
        adapter_ids: list[int] | None,
        debug: bool = False,
        log_debug: bool = False,
    ) -> Callable[[_queue.Queue, threading.Event], dict | None]:
        debug_dir = debug_dir_root / "count" if (debug and debug_dir_root) else None

        def run_fn(q: _queue.Queue, cancel_event: threading.Event) -> dict | None:
            workflow = workflow_class(
                cache_service=cache_service,
                window_interaction_service=window_service,
                network_manager=network_manager,
                screenshot_service=screenshot_service,
                detector=detector,
                network_adapter_ids=adapter_ids,
                debug_dir=debug_dir,
            )
            sink_id = logger.add(
                _make_log_sink(q), level="DEBUG" if log_debug else "INFO"
            )
            try:
                result = workflow.run(cancel_event=cancel_event)
                return {
                    "fail_count": result.fail_count,
                    "stop_reason": result.stop_reason.value,
                }
            finally:
                logger.remove(sink_id)

        return run_fn

    return factory
