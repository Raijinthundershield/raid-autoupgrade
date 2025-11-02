"""Stop condition strategies for upgrade monitoring.

This module provides composable stop conditions that can be used
to determine when to halt upgrade monitoring.
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from loguru import logger

from autoraid.orchestration.progress_bar_monitor import ProgressBarMonitorState
from autoraid.detection.progress_bar_detector import ProgressBarState


class StopReason(Enum):
    """Reasons for stopping upgrade monitoring."""

    MAX_ATTEMPTS_REACHED = "max_attempts_reached"
    MAX_FRAMES_CAPTURED = "max_frames_captured"
    UPGRADED = "upgraded"
    CONNECTION_ERROR = "connection_error"
    MANUAL_STOP = "manual_stop"


class StopCondition(ABC):
    """Abstract base for stop condition strategies.

    Each concrete condition implements a single stop criterion.
    Conditions are checked in order by UpgradeOrchestrator.
    """

    @abstractmethod
    def check(self, state: ProgressBarMonitorState) -> bool:
        pass

    @abstractmethod
    def get_reason(self) -> StopReason:
        pass


@dataclass
class MaxAttemptsCondition(StopCondition):
    """Stop when fail count reaches maximum attempts."""

    max_attempts: int

    def __post_init__(self):
        if self.max_attempts <= 0:
            raise ValueError(f"max_attempts must be positive, got {self.max_attempts}")

    def check(self, state: ProgressBarMonitorState) -> bool:
        if state.fail_count >= self.max_attempts:
            logger.warning(
                f"Max attempts reached: {state.fail_count}/{self.max_attempts}"
            )
            return True
        return False

    def get_reason(self) -> StopReason:
        return StopReason.MAX_ATTEMPTS_REACHED


@dataclass
class MaxFramesCondition(StopCondition):
    """Stop when frames processed reaches maximum."""

    max_frames: int

    def __post_init__(self):
        if self.max_frames <= 0:
            raise ValueError(f"max_frames must be positive, got {self.max_frames}")

    def check(self, state: ProgressBarMonitorState) -> bool:
        if state.frames_processed >= self.max_frames:
            logger.info(
                f"Max frames captured: {state.frames_processed}/{self.max_frames}"
            )
            return True
        return False

    def get_reason(self) -> StopReason:
        return StopReason.MAX_FRAMES_CAPTURED


@dataclass
class UpgradedCondition(StopCondition):
    """Stop when piece has upgraded (detected via consecutive state patterns).

    Two detection modes based on network state:
    1. Network enabled: 4 consecutive STANDBY states (normal confirmation)
    2. Network disabled: 4 consecutive CONNECTION_ERROR states
       (server cannot respond, but piece upgraded locally)

    When network is disabled, the game upgrades the piece locally but cannot
    sync with server. This results in CONNECTION_ERROR states instead of STANDBY.
    Both patterns indicate successful upgrade.
    """

    network_disabled: bool = False

    def check(self, state: ProgressBarMonitorState) -> bool:
        # Need at least 4 states to check
        if len(state.recent_states) < 4:
            return False

        # Check for 4 consecutive STANDBY (normal upgrade confirmation)
        if all(s == ProgressBarState.STANDBY for s in state.recent_states):
            logger.debug("Upgrade detected: 4 consecutive STANDBY states")
            return True

        # If network disabled, CONNECTION_ERROR also indicates successful upgrade
        # (piece upgraded locally, but server cannot confirm)
        if self.network_disabled:
            if all(s == ProgressBarState.CONNECTION_ERROR for s in state.recent_states):
                logger.debug(
                    "Upgrade detected: 4 consecutive CONNECTION_ERROR "
                    "(network disabled - local upgrade success)"
                )
                return True

        return False

    def get_reason(self) -> StopReason:
        return StopReason.UPGRADED


@dataclass
class ConnectionErrorCondition(StopCondition):
    """Stop when 4 consecutive CONNECTION_ERROR states detected (network issue).

    Only used when network should be enabled. Indicates genuine connection problem.
    """

    def check(self, state: ProgressBarMonitorState) -> bool:
        # Need at least 4 states to check
        if len(state.recent_states) < 4:
            return False

        if all(s == ProgressBarState.CONNECTION_ERROR for s in state.recent_states):
            logger.warning("Connection error: 4 consecutive CONNECTION_ERROR states")
            return True

        return False

    def get_reason(self) -> StopReason:
        return StopReason.CONNECTION_ERROR


class StopConditionChain:
    """Manages ordered list of stop conditions and evaluates them.

    Conditions are checked in the order they're added. First matching
    condition determines the stop reason.
    """

    def __init__(self, conditions: list[StopCondition]):
        self._conditions = conditions

    def check(self, state: ProgressBarMonitorState) -> StopReason | None:
        for condition in self._conditions:
            if condition.check(state):
                return condition.get_reason()
        return None

    def should_stop(self, state: ProgressBarMonitorState) -> bool:
        return self.check(state) is not None
