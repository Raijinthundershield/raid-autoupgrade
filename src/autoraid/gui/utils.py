"""GUI utility functions and helpers.

Provides log streaming, async wrappers, and state management utilities.
"""

from loguru import logger


# Global reference to the GUI log element (set by upgrade_panel)
_gui_log_element = None


def set_log_element(log_element):
    """Set the global log element for log streaming.

    Args:
        log_element: NiceGUI ui.log() element to push logs to
    """
    global _gui_log_element
    _gui_log_element = log_element


def get_log_element():
    """Get the global log element.

    Returns:
        The GUI log element if set, None otherwise
    """
    return _gui_log_element


def setup_log_streaming():
    """Set up loguru sink to stream logs to the GUI log element.

    This function configures loguru to capture all logs and push them to the
    GUI log element with color coding based on log level.

    Color mapping:
    - INFO: green
    - DEBUG: blue
    - WARNING: yellow
    - ERROR: red
    """

    def log_sink(message):
        """Loguru sink function that pushes logs to the GUI element.

        Args:
            message: Loguru message object
        """
        log_element = get_log_element()
        if log_element is None:
            return

        # Extract log level and message text
        record = message.record
        level = record["level"].name
        text = record["message"]

        # Push to GUI log element with level prefix
        # Format: [LEVEL] message
        # Color coding is handled by NiceGUI's default log styling
        formatted_message = f"[{level}] {text}"
        log_element.push(formatted_message)

    # Add the sink to loguru
    logger.add(log_sink, format="{message}", level="DEBUG")


def clear_logs():
    """Clear the GUI log element."""
    log_element = get_log_element()
    if log_element is not None:
        log_element.clear()
