"""Centralized logging configuration for AutoRaid.

Provides unified logging format configuration for CLI and GUI.
"""

from loguru import logger


def format_short_name(record):
    """Extract short module name for clean display.

    Adds 'short_name' to record extras containing module.function format.
    Used for INFO level output.

    Args:
        record: Loguru record dict
    """
    module_name = record["name"].split(".")[-1]
    function_name = record["function"]
    record["extra"]["short_name"] = f"{module_name}.{function_name}"


def add_logger_sink(debug: bool, sink, colorize: bool = False, **kwargs):
    """Configure logger with appropriate format based on debug mode.

    Args:
        debug: If True, use detailed DEBUG format; if False, use clean INFO format
        sink: Callable sink function to send formatted logs to
        colorize: Enable color tags in format (for terminal output, not GUI)
        **kwargs: Additional parameters to pass to logger.add() (e.g., rotation, retention)
    """
    if debug:
        # DEBUG mode: detailed format with timestamps, module, function, line
        if colorize:
            format_str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        else:
            format_str = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"

        logger.add(
            sink=sink,
            format=format_str,
            level="DEBUG",
            colorize=colorize,
            **kwargs,
        )
    else:
        # INFO mode: clean format with timestamps and short module.function names
        if colorize:
            format_str = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <cyan>{extra[short_name]: <35}</cyan> | <level>{message}</level>"
        else:
            format_str = (
                "{time:YYYY-MM-DD HH:mm:ss} | {extra[short_name]: <35} | {message}"
            )

        logger.add(
            sink=sink,
            format=format_str,
            level="INFO",
            colorize=colorize,
            filter=lambda record: format_short_name(record) or True,
            **kwargs,
        )
