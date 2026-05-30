"""Custom exception classes for Raid Autoupgrade.

This module defines custom exceptions used throughout the application to provide
clear error messages and facilitate error handling.
"""


class RaidAutoupgradeError(Exception):
    """Base exception class for all Raid Autoupgrade errors."""

    pass


class CacheInitializationError(RaidAutoupgradeError):
    """Raised when cache initialization fails."""

    pass


class WindowNotFoundException(RaidAutoupgradeError):
    """Raised when a window with the specified title cannot be found."""

    pass


class RegionDetectionError(RaidAutoupgradeError):
    """Raised when automatic region detection fails."""

    pass


class DependencyResolutionError(RaidAutoupgradeError):
    """Raised when dependency injection container fails to resolve a dependency."""

    pass


class NetworkAdapterError(RaidAutoupgradeError):
    """Raised when network adapter operations fail."""

    pass


class UpgradeWorkflowError(RaidAutoupgradeError):
    """Raised when an upgrade workflow encounters an error."""

    pass


class WorkflowValidationError(RaidAutoupgradeError):
    """Raised when workflow validation fails before execution."""

    pass
