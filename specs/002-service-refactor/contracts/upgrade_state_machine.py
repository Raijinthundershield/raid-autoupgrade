"""Upgrade state machine interface protocol."""

from typing import Protocol
from enum import Enum
import numpy as np


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


class UpgradeStateMachineProtocol(Protocol):
    """Interface for upgrade state tracking."""

    def process_frame(
        self, roi_image: np.ndarray
    ) -> tuple[int, StopCountReason | None]:
        """Process progress bar frame and return (fail_count, stop_reason).

        Args:
            roi_image: Progress bar region as numpy array (BGR format)

        Returns:
            Tuple of (current fail_count, stop_reason if stop condition met else None)

        Stop conditions:
        - 4 consecutive STANDBY states → StopCountReason.UPGRADED
        - 4 consecutive CONNECTION_ERROR states → StopCountReason.CONNECTION_ERROR
        - fail_count >= max_attempts → StopCountReason.MAX_ATTEMPTS_REACHED
        """
        ...
