"""State machine for tracking upgrade attempts and detecting stop conditions."""

from collections import deque
from enum import Enum

import numpy as np
from loguru import logger

from autoraid.core.progress_bar_detector import (
    ProgressBarState,
    ProgressBarStateDetector,
)


class StopReason(Enum):
    """Reason for stopping upgrade attempt monitoring."""

    MAX_ATTEMPTS_REACHED = "max_attempts_reached"
    SUCCESS = "upgraded"
    CONNECTION_ERROR = "connection_error"


class UpgradeAttemptMonitor:
    """Stateful monitor for upgrade attempt tracking and stop detection.

    Tracks failure count, maintains state history (last 4 states), and
    determines when to stop monitoring based on configured conditions.

    Uses dependency injection to receive detector instance.
    """

    def __init__(self, detector: ProgressBarStateDetector, max_attempts: int):
        """Initialize monitor with detector and max attempts.

        Args:
            detector: ProgressBarStateDetector instance (injected by DI container)
            max_attempts: Maximum failures before stopping (must be positive integer)

        Raises:
            ValueError: If max_attempts <= 0
        """
        if max_attempts <= 0:
            raise ValueError(f"max_attempts must be positive, got {max_attempts}")

        self._detector = detector
        self._max_attempts = max_attempts
        self._fail_count = 0
        self._recent_states: deque[ProgressBarState] = deque(maxlen=4)

        logger.debug(
            f"UpgradeAttemptMonitor initialized with max_attempts={max_attempts}"
        )

    def process_frame(self, roi_image: np.ndarray) -> ProgressBarState:
        """Process frame and update internal state.

        Calls detector to get current state, updates failure count on
        FAIL transitions, appends state to history, and logs transition.

        Args:
            roi_image: BGR numpy array of progress bar region

        Returns:
            Detected ProgressBarState

        Raises:
            ValueError: If roi_image is invalid (propagated from detector)

        Side Effects:
            - Calls self._detector.detect_state(roi_image)
            - Increments self._fail_count if transition to FAIL detected
            - Appends state to self._recent_states (auto-evicts oldest if >4)
            - Logs state transition at DEBUG level
        """
        # Get previous state before detection
        previous_state = self._recent_states[-1] if self._recent_states else None

        # Detect current state
        current_state = self._detector.detect_state(roi_image)

        # Count fail transitions (only when transitioning from non-FAIL to FAIL)
        if (
            current_state == ProgressBarState.FAIL
            and previous_state != ProgressBarState.FAIL
        ):
            self._fail_count += 1

        # Update state history
        self._recent_states.append(current_state)

        # Log state transition
        if previous_state and previous_state != current_state:
            logger.debug(
                f"State transition: {previous_state.value} → {current_state.value}"
                f" (fail_count={self._fail_count})"
            )
        elif previous_state is None:
            logger.debug(f"Initial state: {current_state.value}")

        return current_state

    @property
    def fail_count(self) -> int:
        """Current failure count (read-only).

        Returns:
            Number of times transition to FAIL state occurred.
            Range: [0, max_attempts]
        """
        return self._fail_count

    @property
    def stop_reason(self) -> StopReason | None:
        """Reason for stopping if stop condition met, None otherwise.

        Evaluates stop conditions on each access (computed property).

        Returns:
            - StopReason.MAX_ATTEMPTS_REACHED if fail_count >= max_attempts
            - StopReason.SUCCESS if last 4 states all STANDBY
            - StopReason.CONNECTION_ERROR if last 4 states all CONNECTION_ERROR
            - None if no stop condition met

        Evaluation Order (priority):
            1. MAX_ATTEMPTS_REACHED (always checked first)
            2. Require at least 4 states in history (return None if <4)
            3. SUCCESS (4 consecutive STANDBY)
            4. CONNECTION_ERROR (4 consecutive CONNECTION_ERROR)
        """
        # Check if max attempts reached (this should be checked first)
        if self._fail_count >= self._max_attempts:
            logger.debug(
                f"Stop condition: MAX_ATTEMPTS_REACHED (fail_count={self._fail_count})"
            )
            return StopReason.MAX_ATTEMPTS_REACHED

        # Need at least 4 states to check for consecutive conditions
        if len(self._recent_states) < 4:
            return None

        # Check for 4 consecutive standby states (success)
        if all(state == ProgressBarState.STANDBY for state in self._recent_states):
            logger.debug("Stop condition: SUCCESS (4 consecutive STANDBY)")
            return StopReason.SUCCESS

        # Check for 4 consecutive connection error states
        if all(
            state == ProgressBarState.CONNECTION_ERROR for state in self._recent_states
        ):
            logger.debug("Stop condition: CONNECTION_ERROR (4 consecutive errors)")
            return StopReason.CONNECTION_ERROR

        return None

    @property
    def current_state(self) -> ProgressBarState | None:
        """Most recently detected state, None if no frames processed yet.

        Returns:
            - Last state from recent_states deque
            - None if process_frame() never called
        """
        return self._recent_states[-1] if self._recent_states else None
