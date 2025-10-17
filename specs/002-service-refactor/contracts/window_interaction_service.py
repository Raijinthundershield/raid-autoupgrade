"""Window interaction service interface protocol."""

from typing import Protocol


class WindowInteractionServiceProtocol(Protocol):
    """Interface for window interaction."""

    def click_region(
        self, window_title: str, region: tuple[int, int, int, int]
    ) -> None:
        """Click center of region within window.

        Args:
            window_title: Title of window to interact with
            region: Region as (left, top, width, height)

        Raises:
            WindowNotFoundException: If window not found
            ValueError: If region coordinates invalid
        """
        ...

    def activate_window(self, window_title: str) -> None:
        """Bring window to foreground.

        Args:
            window_title: Title of window to activate

        Raises:
            WindowNotFoundException: If window not found
        """
        ...
