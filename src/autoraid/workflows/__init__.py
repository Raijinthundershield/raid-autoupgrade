"""
Workflow system for AutoRaid upgrade automation.

This package provides workflow classes that coordinate services to execute
upgrade counting and spending operations with explicit validation lifecycles.
"""

from autoraid.workflows.count_workflow import CountResult, CountWorkflow
from autoraid.workflows.debug_monitor_workflow import (
    DebugMonitorResult,
    DebugMonitorWorkflow,
)
from autoraid.workflows.spend_workflow import SpendResult, SpendWorkflow

__all__ = [
    "CountWorkflow",
    "CountResult",
    "SpendWorkflow",
    "SpendResult",
    "DebugMonitorWorkflow",
    "DebugMonitorResult",
]
