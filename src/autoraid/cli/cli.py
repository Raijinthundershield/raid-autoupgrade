import click
from diskcache import Cache
from loguru import logger

from autoraid.cli.upgrade_cli import upgrade
from autoraid.cli.network_cli import network
from autoraid.cli.debug_cli import debug
from autoraid.container import Container
from autoraid.logging_config import add_logger_sink
from autoraid.services.app_data import AppData


@click.group()
@click.option(
    "--debug",
    "-d",
    is_flag=True,
    default=False,
    help="Save screenshots and other information to debug directory within cache directory.",
)
def autoraid(debug: bool):
    """Raid: Shadow Legends auto-upgrade tool.

    This tool helps automate the process of upgrading equipment in Raid: Shadow Legends
    by monitoring upgrade attempts.

    """

    # Create and configure DI container
    container = Container()
    container.config.cache_dir.from_value(AppData.DEFAULT_CACHE_DIR)
    container.config.debug.from_value(debug)
    container.wire()

    # Create app_data and ensure directories exist
    app_data = container.app_data()
    app_data.ensure_directories()

    # Initialize cache (still needed for backward compatibility)
    cache = Cache(str(app_data.cache_dir))

    # Store in context
    ctx = click.get_current_context()
    ctx.obj = {
        "cache": cache,
        "cache_dir": app_data.cache_dir,
        "container": container,
        "app_data": app_data,
        "debug": debug,
    }

    # Configure logging based on debug mode
    logger.remove()  # Remove default handler

    def console_sink(msg):
        click.echo(msg, err=True)

    add_logger_sink(debug, console_sink, colorize=True)

    # Add file logging if debug enabled
    log_file = app_data.get_log_file_path()
    if log_file:
        add_logger_sink(debug, log_file, colorize=False, rotation="10 MB")
        logger.debug(f"Debug mode enabled. Logging to {log_file}")


autoraid.add_command(upgrade)
autoraid.add_command(network)
autoraid.add_command(debug)


@autoraid.command()
@click.pass_context
def gui(ctx):
    """Launch the native desktop GUI interface.

    Opens a native desktop window with a graphical interface for managing
    upgrade workflows, network adapters, and UI regions.
    """
    from autoraid.gui.app import main

    debug = ctx.obj.get("debug", False)
    main(debug=debug)
