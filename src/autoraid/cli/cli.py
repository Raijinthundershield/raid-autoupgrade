import click
from diskcache import Cache
from loguru import logger

from autoraid.cli.debug_cli import debug
from autoraid.cli.network_cli import network
from autoraid.cli.upgrade_cli import upgrade
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
@click.pass_context
def autoraid(ctx: click.Context, debug: bool):
    """Raid: Shadow Legends auto-upgrade tool.

    This tool helps automate the process of upgrading equipment in Raid: Shadow Legends
    by monitoring upgrade attempts.

    """
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug

    # gui manages its own services — skip the container and cache setup
    if ctx.invoked_subcommand == "gui":
        return

    # Create and configure DI container
    container = Container()
    container.config.cache_dir.from_value(AppData.DEFAULT_ROOT)
    container.config.debug.from_value(debug)
    container.wire()

    # Create app_data and ensure directories exist
    app_data = container.app_data()
    app_data.ensure_directories()

    # Initialize cache (still needed for backward compatibility)
    cache = Cache(str(app_data.cache_dir))

    ctx.obj.update(
        {
            "cache": cache,
            "cache_dir": app_data.cache_dir,
            "container": container,
            "app_data": app_data,
        }
    )

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
    from autoraid.gui.server import start

    debug = ctx.obj.get("debug", False)
    start(debug=debug)
