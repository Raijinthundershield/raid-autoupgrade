"""Factories that build workflow run_fn callables for JobRegistry.start_job."""

import queue as _queue
import threading
from collections.abc import Callable
from pathlib import Path

from loguru import logger

from autoraid.orchestration.upgrade_orchestrator import ProgressEvent
from autoraid.workflows.count_workflow import CountWorkflow
from autoraid.workflows.spend_workflow import SpendWorkflow


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


def _make_progress_callback(q: _queue.Queue) -> Callable[[ProgressEvent], None]:
    def on_progress(event: ProgressEvent) -> None:
        q.put(
            {
                "type": "progress",
                "fail_count": event.fail_count,
                "frames": event.frames,
                "state": event.state.value if event.state is not None else None,
            }
        )

    return on_progress


def make_count_runner(
    cache_service,
    window_service,
    network_manager,
    screenshot_service,
    detector,
    debug_dir_root: Path | None = None,
    workflow_class=CountWorkflow,
    settings_service=None,
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
                result = workflow.run(
                    cancel_event=cancel_event,
                    on_progress=_make_progress_callback(q),
                )
                result_dict = {
                    "fail_count": result.fail_count,
                    "stop_reason": result.stop_reason.value,
                }
                if settings_service is not None:
                    from autoraid.services.settings_service import Settings

                    current = settings_service.get_settings()
                    settings_service.save_settings(
                        Settings(
                            selected_adapters=current.selected_adapters,
                            last_count_result=result_dict,
                        )
                    )
                return result_dict
            finally:
                logger.remove(sink_id)

        return run_fn

    return factory


def make_spend_runner(
    cache_service,
    window_service,
    network_manager,
    screenshot_service,
    detector,
    debug_dir_root: Path | None = None,
    workflow_class=SpendWorkflow,
) -> Callable[
    [int, bool],
    Callable[[_queue.Queue, threading.Event], dict | None],
]:
    """Return a factory: (max_upgrade_attempts, continue_upgrade) → run_fn for JobRegistry.start_job."""

    def factory(
        max_upgrade_attempts: int,
        continue_upgrade: bool = False,
    ) -> Callable[[_queue.Queue, threading.Event], dict | None]:
        def run_fn(q: _queue.Queue, cancel_event: threading.Event) -> dict | None:
            workflow = workflow_class(
                cache_service=cache_service,
                window_interaction_service=window_service,
                network_manager=network_manager,
                screenshot_service=screenshot_service,
                detector=detector,
                max_upgrade_attempts=max_upgrade_attempts,
                continue_upgrade=continue_upgrade,
            )
            sink_id = logger.add(_make_log_sink(q), level="INFO")
            try:
                result = workflow.run(
                    cancel_event=cancel_event,
                    on_progress=_make_progress_callback(q),
                )
                return {
                    "upgrade_count": result.upgrade_count,
                    "attempt_count": result.attempt_count,
                    "remaining_attempts": result.remaining_attempts,
                    "stop_reason": result.stop_reason.value,
                }
            finally:
                logger.remove(sink_id)

        return run_fn

    return factory
