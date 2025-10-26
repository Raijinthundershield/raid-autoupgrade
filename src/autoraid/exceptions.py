"""Custom exception classes for AutoRaid.

This module defines custom exceptions used throughout the application to provide
clear error messages and facilitate error handling.
"""


class AutoRaidError(Exception):
    """Base exception class for all AutoRaid errors."""

    pass


class CacheInitializationError(AutoRaidError):
    """Raised when cache initialization fails."""

    pass


class WindowNotFoundException(AutoRaidError):
    """Raised when a window with the specified title cannot be found."""

    pass


class RegionDetectionError(AutoRaidError):
    """Raised when automatic region detection fails."""

    pass


class DependencyResolutionError(AutoRaidError):
    """Raised when dependency injection container fails to resolve a dependency."""

    pass


class NetworkAdapterError(AutoRaidError):
    """Raised when network adapter operations fail."""

    pass


class UpgradeWorkflowError(AutoRaidError):
    """Raised when an upgrade workflow encounters an error."""

    pass


class WorkflowValidationError(AutoRaidError):
    """Raised when workflow validation fails before execution."""

    pass
