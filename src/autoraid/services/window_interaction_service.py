"""Window interaction service for clicking and activating windows.

This service handles all window interaction operations including:
- Checking window existence
- Clicking regions within windows
- Activating windows with multi-strategy UIPI bypass
"""

import ctypes
import time
from ctypes import wintypes

import pyautogui
import pygetwindow
from loguru import logger

from autoraid.exceptions import WindowNotFoundException


# Win32 Constants
SW_MINIMIZE = 6
SW_RESTORE = 9
VK_MENU = 0x12  # ALT key
KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1


# Win32 Structures for SendInput
class KEYBDINPUT(ctypes.Structure):
    """Keyboard input structure for SendInput."""

    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.WPARAM),  # WPARAM is ULONG_PTR
    ]


class INPUT(ctypes.Structure):
    """Input structure for SendInput."""

    class _INPUTUnion(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]

    _fields_ = [("type", wintypes.DWORD), ("union", _INPUTUnion)]


# Win32 Structures for GetWindowPlacement
class RECT(ctypes.Structure):
    """Rectangle structure for window coordinates."""

    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class POINT(ctypes.Structure):
    """Point structure for window coordinates.

    Note: Required by WINDOWPLACEMENT for Win32 API correctness.
    ptMinPosition and ptMaxPosition fields are not currently accessed.
    """

    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class WINDOWPLACEMENT(ctypes.Structure):
    """Window placement structure containing window state and positions."""

    _fields_ = [
        ("length", wintypes.UINT),
        ("flags", wintypes.UINT),
        ("showCmd", wintypes.UINT),
        ("ptMinPosition", POINT),
        ("ptMaxPosition", POINT),
        ("rcNormalPosition", RECT),
    ]


class WindowInteractionService:
    """Service for window interaction operations.

    Responsibilities:
    - Check window existence
    - Click regions within windows
    - Activate windows using multi-strategy approach to bypass UIPI restrictions

    Window Activation Strategies (tried in order):
    1. ALT + SetForegroundWindow - Invisible, works across privilege boundaries
    2. Minimize/Restore trick - Guaranteed to work but visually disruptive
    """

    def __init__(self) -> None:
        """Initialize WindowInteractionService with Win32 API references."""
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32

    def window_exists(self, window_title: str) -> bool:
        """Check if a window with the given title exists.

        Args:
            window_title: Title of the window to check for

        Returns:
            True if window exists, False otherwise

        Raises:
            ValueError: If window_title is empty
        """
        logger.debug(f'window_exists called with window_title="{window_title}"')

        if not window_title:
            raise ValueError("window_title cannot be empty")

        windows = pygetwindow.getAllWindows()

        if not windows:
            logger.warning("No active windows found!")
            return False

        for window in windows:
            if window.title == window_title:
                logger.debug(f'Window "{window_title}" found')
                return True

        logger.debug(f'Window "{window_title}" not found')
        return False

    def click_region(
        self, window_title: str, region: tuple[int, int, int, int]
    ) -> None:
        """Click in the center of a region relative to the window.

        Args:
            window_title: Title of the window to click in
            region: Region coordinates (left, top, width, height) relative to the window

        Raises:
            WindowNotFoundException: If window not found
            ValueError: If window_title is empty or region is invalid
        """
        logger.info("Clicking region")
        logger.debug(
            f'click_region called with window_title="{window_title}", region={region}'
        )

        if not window_title:
            raise ValueError("window_title cannot be empty")

        left, top, width, height = region

        # Validate region dimensions
        if width <= 0 or height <= 0:
            raise ValueError(
                f"Invalid region dimensions: width={width}, height={height}. "
                f"Dimensions must be positive."
            )

        try:
            # Activate window using minimize trick for reliability
            self.activate_window(window_title)

            # Get fresh window reference for coordinates
            windows = pygetwindow.getWindowsWithTitle(window_title)
            if not windows:
                raise WindowNotFoundException(
                    f'Window "{window_title}" not found. '
                    f"Ensure the application is running."
                )

            window = windows[0]

            # Calculate center of region relative to window
            center_x = left + width // 2
            center_y = top + height // 2

            # Calculate absolute screen coordinates
            screen_x = window.left + center_x
            screen_y = window.top + center_y

            logger.info(f"Clicking at ({screen_x}, {screen_y})")

            pyautogui.click(screen_x, screen_y)
            time.sleep(0.05)

        except IndexError:
            logger.error(f'Window "{window_title}" not found')
            raise WindowNotFoundException(
                f'Window "{window_title}" not found. Ensure the application is running.'
            )
        except Exception as e:
            logger.error(f"Failed to click region: {e}")
            raise

    def get_window_size(self, window_title: str) -> tuple[int, int]:
        """Get the restored size of the specified window.

        Uses Win32 GetWindowPlacement to get the restored window dimensions,
        which works correctly even when the window is minimized. This ensures
        consistent size reporting regardless of window state (normal, minimized,
        or maximized).

        Args:
            window_title: Title of the window to get size for

        Returns:
            Tuple of (height, width) in pixels of the restored window

        Raises:
            WindowNotFoundException: If window not found
            ValueError: If window_title is empty
        """
        logger.debug(f'get_window_size called with window_title="{window_title}"')

        if not window_title:
            raise ValueError("window_title cannot be empty")

        try:
            # Get window handle
            hwnd = self._get_hwnd(window_title)

            # Get window placement to retrieve restored rectangle
            placement = WINDOWPLACEMENT()
            placement.length = ctypes.sizeof(WINDOWPLACEMENT)

            if not self._user32.GetWindowPlacement(hwnd, ctypes.byref(placement)):
                error_code = self._kernel32.GetLastError()
                raise RuntimeError(
                    f"GetWindowPlacement failed with Win32 error code {error_code}"
                )

            # Extract restored rectangle dimensions
            rect = placement.rcNormalPosition
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            size = (height, width)

            logger.debug(f"get_window_size returned restored size {size[0]}x{size[1]}")

            return size

        except WindowNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to get window size: {e}")
            raise

    def _get_hwnd(self, window_title: str) -> int:
        """Get window handle (HWND) from window title.

        Args:
            window_title: Title of the window

        Returns:
            Window handle (HWND)

        Raises:
            WindowNotFoundException: If window not found
        """
        windows = pygetwindow.getWindowsWithTitle(window_title)
        if not windows:
            raise WindowNotFoundException(
                f'Window "{window_title}" not found. '
                f"Ensure the application is running."
            )

        window = windows[0]
        # pygetwindow stores HWND in _hWnd attribute
        return window._hWnd

    def _activate_with_alt_key(self, hwnd: int) -> bool:
        """Activate window using ALT key + SetForegroundWindow.

        This method simulates pressing the ALT key, which makes Windows
        automatically grant SetForegroundWindow permission. This bypasses
        UIPI restrictions without visual disruption.

        Args:
            hwnd: Window handle

        Returns:
            True if activation succeeded, False otherwise
        """
        try:
            # Create INPUT structures for ALT key press and release
            inputs = (INPUT * 2)()
            inputs[0].type = INPUT_KEYBOARD
            inputs[0].union.ki.wVk = VK_MENU
            inputs[1].type = INPUT_KEYBOARD
            inputs[1].union.ki.wVk = VK_MENU
            inputs[1].union.ki.dwFlags = KEYEVENTF_KEYUP

            # Send ALT key press/release
            result = self._user32.SendInput(
                2, ctypes.byref(inputs), ctypes.sizeof(INPUT)
            )
            if result == 0:
                logger.debug("SendInput failed")
                return False

            # Small delay to ensure input is processed
            time.sleep(0.01)

            # Try to set foreground window
            success = self._user32.SetForegroundWindow(hwnd)
            if success:
                time.sleep(0.05)  # Brief wait for window to activate
                return True

            return False

        except Exception as e:
            logger.debug(f"ALT key activation failed: {e}")
            return False

    def _activate_with_minimize_trick(self, hwnd: int) -> bool:
        """Activate window using minimize/restore trick.

        This method minimizes and then restores the window, which changes
        window state in a way that grants activation permission. Works
        across privilege boundaries but causes visible flicker.

        Args:
            hwnd: Window handle

        Returns:
            True if activation succeeded, False otherwise
        """
        try:
            self._user32.ShowWindow(hwnd, SW_MINIMIZE)
            time.sleep(0.05)
            self._user32.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.05)
            success = self._user32.SetForegroundWindow(hwnd)
            time.sleep(0.1)
            return bool(success)

        except Exception as e:
            logger.debug(f"Minimize trick activation failed: {e}")
            return False

    def _ensure_window_restored(self, hwnd: int, window_title: str) -> None:
        """Ensure window is restored from minimized state after activation.

        After activating a window, it may still be minimized. This method
        checks if the window is minimized and explicitly restores it.

        Args:
            hwnd: Window handle
            window_title: Title of the window (for logging and verification)
        """
        try:
            windows = pygetwindow.getWindowsWithTitle(window_title)
            if windows and windows[0].isMinimized:
                logger.debug("Window is minimized after activation, restoring...")
                self._user32.ShowWindow(hwnd, SW_RESTORE)
                time.sleep(0.1)  # Wait for restore to complete
                logger.debug("Window restored from minimized state")
        except Exception as e:
            logger.debug(f"Failed to check/restore minimized state: {e}")
            # Don't raise - this is a best-effort operation

    def activate_window(self, window_title: str) -> None:
        """Activate (bring to foreground) the specified window.

        Uses a multi-strategy approach with automatic fallback:
        1. ALT + SetForegroundWindow (invisible, UIPI-safe)
        2. Minimize/Restore trick (guaranteed fallback)

        Args:
            window_title: Title of the window to activate

        Raises:
            WindowNotFoundException: If window not found
            ValueError: If window_title is empty
            RuntimeError: If all activation strategies fail
        """
        logger.debug(f'activate_window called with window_title="{window_title}"')

        if not window_title:
            raise ValueError("window_title cannot be empty")

        try:
            # Get window handle and state in single lookup
            windows = pygetwindow.getWindowsWithTitle(window_title)
            if not windows:
                raise WindowNotFoundException(
                    f'Window "{window_title}" not found. '
                    f"Ensure the application is running."
                )

            window = windows[0]
            hwnd = window._hWnd
            is_active = window.isActive and not window.isMinimized

            if is_active:
                logger.debug(f'Window "{window_title}" is already active')
                return

            logger.debug(
                f"Window not active: isMinimized={window.isMinimized}, "
                f"isActive={window.isActive}"
            )

            # Strategy 1: ALT + SetForegroundWindow (invisible, UIPI-safe)
            logger.debug("Attempting ALT key activation strategy")
            if self._activate_with_alt_key(hwnd):
                logger.debug("Window activated using ALT key method")
                self._ensure_window_restored(hwnd, window_title)
                return

            # Strategy 2: Minimize/Restore trick (guaranteed but visible)
            logger.debug("Attempting minimize trick activation strategy")
            if self._activate_with_minimize_trick(hwnd):
                logger.debug("Window activated using minimize trick")
                # Minimize trick already restores the window, no need to check
                return

            # All strategies failed
            logger.error("All activation strategies failed")
            raise RuntimeError(
                f'Failed to activate window "{window_title}" after trying all strategies'
            )

        except WindowNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to activate window: {e}")
            raise
