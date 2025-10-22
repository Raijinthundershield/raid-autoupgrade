"""State machine for tracking upgrade attempts and detecting stop conditions."""

from collections import deque
from enum import Enum

import numpy as np
from loguru import logger

from autoraid.core import progress_bar


class ProgressBarState(Enum):
    """Progress bar state detected from color analysis."""

    FAIL = "fail"
    PROGRESS = "progress"
    STANDBY = "standby"
    CONNECTION_ERROR = "connection_error"
    UNKNOWN = "unknown"


class StopCountReason(Enum):
    """Reason for stopping count workflow."""

    UPGRADED = "upgraded"
    CONNECTION_ERROR = "connection_error"
    MAX_ATTEMPTS_REACHED = "max_attempts_reached"


class UpgradeStateMachine:
    """State machine for tracking upgrade attempts and counting failures.

    This class separates the pure state machine logic from I/O operations,
    making it testable with fixture images without requiring a live Raid window.
    """

    def __init__(self, max_attempts: int = 100):
        """Initialize state machine with max attempts limit.

        Args:
            max_attempts: Maximum number of upgrade attempts before stopping
        """
        if max_attempts <= 0:
            raise ValueError("max_attempts must be greater than 0")

        self.max_attempts = max_attempts
        self.fail_count = 0
        self.recent_states: deque[ProgressBarState] = deque(maxlen=4)

        logger.debug(f"Initialized with max_attempts={max_attempts}")

    def process_frame(
        self, roi_image: np.ndarray
    ) -> tuple[int, StopCountReason | None]:
        """Process progress bar frame and return fail count and stop reason.

        Args:
            roi_image: Progress bar region of interest image

        Returns:
            Tuple of (fail_count, stop_reason). stop_reason is None if not stopped.
        """
        if roi_image is None or roi_image.size == 0:
            raise ValueError("roi_image must be a valid numpy array")

        # Detect current state
        previous_state = self.recent_states[-1] if self.recent_states else None
        state = self._detect_state(roi_image)

        # Log state transitions
        if previous_state and previous_state != state:
            logger.debug(f"State transition: {previous_state.value} → {state.value}")
        elif previous_state is None:
            logger.debug(f"State transition: {previous_state} → {state.value}")

        # Update recent states
        self.recent_states.append(state)

        # Count fail states
        if state == ProgressBarState.FAIL and previous_state != ProgressBarState.FAIL:
            self.fail_count += 1
            logger.debug(f"Fail detected, count now: {self.fail_count}")

        # Log warning for unknown states
        if state == ProgressBarState.UNKNOWN:
            logger.debug("Unknown progress bar state detected")

        # Check stop conditions
        stop_reason = self._check_stop_condition()
        if stop_reason:
            logger.info(f"Stop condition met: {stop_reason.value}")

        return self.fail_count, stop_reason

    def _detect_state(self, roi_image: np.ndarray) -> ProgressBarState:
        """Detect progress bar state from image using color analysis.

        Args:
            roi_image: Progress bar region of interest image

        Returns:
            Detected progress bar state
        """
        # Use existing progress_bar module for detection
        state_str = progress_bar.get_progress_bar_state(roi_image)

        # Map string to enum
        try:
            return ProgressBarState(state_str)
        except ValueError:
            logger.warning(f"Unexpected state string: {state_str}")
            return ProgressBarState.UNKNOWN

    def _check_stop_condition(self) -> StopCountReason | None:
        """Check if any stop condition is met.

        Returns:
            Stop reason if condition met, None otherwise
        """
        # Check if max attempts reached (this should be checked first)
        if self.fail_count >= self.max_attempts:
            return StopCountReason.MAX_ATTEMPTS_REACHED

        # Need at least 4 states to check for consecutive conditions
        if len(self.recent_states) < 4:
            return None

        # Check for 4 consecutive standby states (upgraded)
        if all(state == ProgressBarState.STANDBY for state in self.recent_states):
            return StopCountReason.UPGRADED

        # Check for 4 consecutive connection error states
        if all(
            state == ProgressBarState.CONNECTION_ERROR for state in self.recent_states
        ):
            return StopCountReason.CONNECTION_ERROR

        return None
