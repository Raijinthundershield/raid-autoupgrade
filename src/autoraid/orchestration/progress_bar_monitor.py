"""Progress bar monitoring without stop condition logic.

This module provides a stateful monitor for progress bar state detection
that is decoupled from stop condition evaluation.
"""

from dataclasses import dataclass
from collections import deque
import numpy as np
from loguru import logger

from autoraid.detection.progress_bar_detector import (
    ProgressBarState,
    ProgressBarStateDetector,
)


@dataclass(frozen=True)
class ProgressBarMonitorState:
    """Immutable snapshot of monitor state at a point in time."""

    frames_processed: int  # Total frames captured
    fail_count: int  # Number of fail state transitions
    recent_states: tuple[ProgressBarState, ...]  # Last 4 states (immutable)
    current_state: ProgressBarState | None  # Most recent state


class ProgressBarMonitor:
    """Stateful monitor for progress bar without stop condition logic.

    Responsibilities:
    - Process frames and detect state
    - Track fail transitions (FAIL state entered from non-FAIL)
    - Maintain recent state history (last 4 states)
    - Provide immutable state snapshots

    NOT responsible for:
    - Stop condition evaluation (delegated to StopCondition classes)
    - Debug data capture (delegated to DebugFrameLogger)
    - Orchestration (delegated to UpgradeOrchestrator)
    - Upgrade counting (workflow-specific logic, handled by SpendWorkflow)
    """

    def __init__(self, detector: ProgressBarStateDetector):
        """Initialize monitor with detector.

        Args:
            detector: Injected ProgressBarStateDetector (singleton)
        """
        self._detector = detector
        self._frames_processed = 0
        self._fail_count = 0
        self._recent_states: deque[ProgressBarState] = deque(maxlen=4)

    def process_frame(self, roi_image: np.ndarray) -> ProgressBarState:
        """Process frame and update internal state.

        Args:
            roi_image: BGR numpy array of progress bar ROI

        Returns:
            Detected ProgressBarState

        Side Effects:
            - Increments frames_processed
            - Updates fail_count if FAIL transition detected
            - Appends state to recent_states (auto-evicts oldest)
            - Logs state transitions (DEBUG level)
        """
        previous_state = self._recent_states[-1] if self._recent_states else None
        current_state = self._detector.detect_state(roi_image)

        # Track fail transitions (entering FAIL from non-FAIL)
        if (
            current_state == ProgressBarState.FAIL
            and previous_state != ProgressBarState.FAIL
        ):
            self._fail_count += 1
            logger.debug(f"Fail transition detected (fail_count={self._fail_count})")

        self._recent_states.append(current_state)
        self._frames_processed += 1

        # Log state transitions
        if previous_state and previous_state != current_state:
            logger.debug(
                f"State transition: {previous_state.value} → {current_state.value} "
                f"(frames={self._frames_processed}, fails={self._fail_count})"
            )
        elif previous_state is None:
            logger.debug(f"Initial state: {current_state.value}")

        return current_state

    def get_state(self) -> ProgressBarMonitorState:
        """Get immutable snapshot of current monitor state.

        Returns:
            Immutable ProgressBarMonitorState dataclass
        """
        return ProgressBarMonitorState(
            frames_processed=self._frames_processed,
            fail_count=self._fail_count,
            recent_states=tuple(self._recent_states),
            current_state=self._recent_states[-1] if self._recent_states else None,
        )

    @property
    def fail_count(self) -> int:
        """Current fail count (convenience accessor)."""
        return self._fail_count

    @property
    def frames_processed(self) -> int:
        """Total frames processed (convenience accessor)."""
        return self._frames_processed

    @property
    def current_state(self) -> ProgressBarState | None:
        """Most recently detected state (convenience accessor)."""
        return self._recent_states[-1] if self._recent_states else None
