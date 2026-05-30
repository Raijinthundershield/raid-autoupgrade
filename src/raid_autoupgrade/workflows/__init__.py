"""
Workflow system for Raid Autoupgrade upgrade automation.

This package provides workflow classes that coordinate services to execute
upgrade counting and spending operations with explicit validation lifecycles.
"""

from raid_autoupgrade.workflows.count_workflow import CountResult, CountWorkflow
from raid_autoupgrade.workflows.debug_monitor_workflow import (
    DebugMonitorResult,
    DebugMonitorWorkflow,
)
from raid_autoupgrade.workflows.spend_workflow import SpendResult, SpendWorkflow

__all__ = [
    "CountWorkflow",
    "CountResult",
    "SpendWorkflow",
    "SpendResult",
    "DebugMonitorWorkflow",
    "DebugMonitorResult",
]
