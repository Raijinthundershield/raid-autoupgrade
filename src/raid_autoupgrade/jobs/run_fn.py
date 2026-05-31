"""Factories that build workflow run_fn callables for JobRegistry.start_job."""

import queue as _queue
import threading
from collections.abc import Callable
from pathlib import Path

import cv2
from loguru import logger

from raid_autoupgrade.constants import RAID_WINDOW_TITLE
from raid_autoupgrade.orchestration.stop_conditions import StopReason
from raid_autoupgrade.orchestration.upgrade_orchestrator import ProgressEvent
from raid_autoupgrade.services.network import AdapterId
from raid_autoupgrade.workflows.count_workflow import CountWorkflow
from raid_autoupgrade.workflows.spend_workflow import SpendProgress, SpendWorkflow


def _stage_target_screenshot(screenshot_service, screenshot_store) -> None:
    """Capture the full Raid window and stage it as the counted-Target picture."""
    try:
        image = screenshot_service.take_screenshot(RAID_WINDOW_TITLE)
        ok, buf = cv2.imencode(".png", image)
        if ok:
            screenshot_store.stage(buf.tobytes())
    except Exception:
        logger.warning("Failed to capture Target screenshot at Count start")


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


def _make_spend_progress_callback(
    q: _queue.Queue,
) -> Callable[[SpendProgress], None]:
    """Serialize cumulative Spend snapshots as the shared ``progress`` event,
    carrying the optional Spend outcome fields the Spend panel self-selects."""

    def on_progress(snapshot: SpendProgress) -> None:
        q.put(
            {
                "type": "progress",
                "attempts_used": snapshot.attempts_used,
                "remaining": snapshot.remaining,
                "upgrades": snapshot.upgrades,
                "state": snapshot.state.value if snapshot.state is not None else None,
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
    screenshot_store=None,
) -> Callable[
    [list[AdapterId] | None],
    Callable[[_queue.Queue, threading.Event], dict | None],
]:
    """Return a factory: (adapter_ids,) → run_fn for JobRegistry.start_job.

    Debug-frame capture is gated by ``debug_dir_root``: the composition root
    passes a root only when the GUI is launched with ``--debug``; otherwise it
    is ``None`` and no debug artifacts are written.
    """

    def factory(
        adapter_ids: list[AdapterId] | None,
    ) -> Callable[[_queue.Queue, threading.Event], dict | None]:
        debug_dir = debug_dir_root / "count" if debug_dir_root else None

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
            # Capture the Target at Count start, before the first upgrade click:
            # the Target is static for the whole Count and the end of a Count is
            # the persistent Connection Error overlay, so the start frame is the
            # only reliably clean capture. Best-effort — a capture glitch must
            # never block counting, the feature is only a visual aid.
            if screenshot_store is not None:
                _stage_target_screenshot(screenshot_service, screenshot_store)

            try:
                result = workflow.run(
                    cancel_event=cancel_event,
                    on_progress=_make_progress_callback(q),
                )
            except Exception:
                if screenshot_store is not None:
                    screenshot_store.discard()
                raise

            result_dict = {
                "fail_count": result.fail_count,
                "stop_reason": result.stop_reason.value,
            }

            # A cancelled Count must leave the previous Target's picture and its
            # matching fail count untouched, so neither is updated here.
            if result.stop_reason == StopReason.MANUAL_STOP:
                if screenshot_store is not None:
                    screenshot_store.discard()
                return result_dict

            # Success: persist the fail count and promote the staged picture in
            # the same step so they stay a matched pair.
            if settings_service is not None:
                from raid_autoupgrade.services.settings_service import Settings

                current = settings_service.get_settings()
                settings_service.save_settings(
                    Settings(
                        selected_adapters=current.selected_adapters,
                        last_count_result=result_dict,
                    )
                )
            if screenshot_store is not None:
                screenshot_store.commit()
            return result_dict

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
    """Return a factory: (max_upgrade_attempts, continue_upgrade) → run_fn for JobRegistry.start_job.

    Debug-frame capture is gated by ``debug_dir_root``: the composition root
    passes a root only when the GUI is launched with ``--debug``; otherwise it
    is ``None`` and no debug artifacts are written.
    """

    def factory(
        max_upgrade_attempts: int,
        continue_upgrade: bool = False,
    ) -> Callable[[_queue.Queue, threading.Event], dict | None]:
        debug_dir = debug_dir_root / "spend" if debug_dir_root else None

        def run_fn(q: _queue.Queue, cancel_event: threading.Event) -> dict | None:
            workflow = workflow_class(
                cache_service=cache_service,
                window_interaction_service=window_service,
                network_manager=network_manager,
                screenshot_service=screenshot_service,
                detector=detector,
                max_upgrade_attempts=max_upgrade_attempts,
                continue_upgrade=continue_upgrade,
                debug_dir=debug_dir,
            )
            result = workflow.run(
                cancel_event=cancel_event,
                on_progress=_make_spend_progress_callback(q),
            )
            return {
                "upgrade_count": result.upgrade_count,
                "attempt_count": result.attempt_count,
                "remaining_attempts": result.remaining_attempts,
                "stop_reason": result.stop_reason.value,
            }

        return run_fn

    return factory
