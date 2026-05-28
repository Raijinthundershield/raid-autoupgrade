"""Factory that builds the count workflow run_fn for JobRegistry.start_job."""

import queue as _queue
from collections.abc import Callable

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
) -> Callable[[list[int] | None], Callable[[_queue.Queue], dict | None]]:
    """Return a factory: adapter_ids → run_fn for JobRegistry.start_job."""

    def factory(adapter_ids: list[int] | None) -> Callable[[_queue.Queue], dict | None]:
        def run_fn(q: _queue.Queue) -> dict | None:
            workflow = CountWorkflow(
                cache_service=cache_service,
                window_interaction_service=window_service,
                network_manager=network_manager,
                screenshot_service=screenshot_service,
                detector=detector,
                network_adapter_ids=adapter_ids,
            )
            sink_id = logger.add(_make_log_sink(q))
            try:
                result = workflow.run()
                return {
                    "fail_count": result.fail_count,
                    "stop_reason": result.stop_reason.value,
                }
            finally:
                logger.remove(sink_id)

        return run_fn

    return factory
