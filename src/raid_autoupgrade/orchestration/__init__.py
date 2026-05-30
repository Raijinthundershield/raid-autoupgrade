"""Application-layer coordination logic."""

from raid_autoupgrade.orchestration.debug_frame_logger import (
    DebugFrame,
    DebugFrameLogger,
)
from raid_autoupgrade.orchestration.progress_bar_monitor import (
    ProgressBarMonitor,
    ProgressBarMonitorState,
)
from raid_autoupgrade.orchestration.stop_conditions import (
    ConnectionErrorCondition,
    MaxAttemptsCondition,
    MaxFramesCondition,
    StopCondition,
    StopConditionChain,
    StopReason,
    UpgradedCondition,
)
from raid_autoupgrade.orchestration.upgrade_orchestrator import (
    UpgradeOrchestrator,
    UpgradeResult,
    UpgradeSession,
)

__all__ = [
    "UpgradeOrchestrator",
    "UpgradeResult",
    "UpgradeSession",
    "ProgressBarMonitor",
    "ProgressBarMonitorState",
    "StopReason",
    "StopCondition",
    "MaxAttemptsCondition",
    "MaxFramesCondition",
    "UpgradedCondition",
    "ConnectionErrorCondition",
    "StopConditionChain",
    "DebugFrame",
    "DebugFrameLogger",
]
