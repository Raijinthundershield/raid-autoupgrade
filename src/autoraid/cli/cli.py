from pathlib import Path
import click
from diskcache import Cache
from loguru import logger

from autoraid.cli.upgrade_cli import upgrade
from autoraid.cli.network_cli import network
from autoraid.container import Container
from autoraid.logging_config import add_logger_sink


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

    # Create cache directory
    cache_dir = Path("cache-raid-autoupgrade")
    cache_dir.mkdir(exist_ok=True)

    # Initialize cache
    cache = Cache(str(cache_dir))

    # Create and configure DI container
    container = Container()
    container.config.from_dict(
        {
            "cache_dir": str(cache_dir),
            "debug": debug,
        }
    )
    container.wire(
        modules=[
            "autoraid.cli.upgrade_cli",
            "autoraid.cli.network_cli",
        ]
    )

    # Store cache and container in context
    ctx = click.get_current_context()
    ctx.obj = {
        "cache": cache,
        "cache_dir": cache_dir,
        "container": container,
    }

    # Configure logging based on debug mode
    logger.remove()  # Remove default handler

    def console_sink(msg):
        click.echo(msg, err=True)

    add_logger_sink(debug, console_sink, colorize=True)

    if debug:
        debug_dir = cache_dir / "debug"
        debug_dir.mkdir(exist_ok=True)

        file_sink = debug_dir / "autoraid.log"
        add_logger_sink(debug, file_sink, colorize=False, rotation="10 MB")
        logger.debug(f"Debug mode enabled. Logging to {file_sink}")
        ctx.obj["debug_dir"] = debug_dir
    else:
        ctx.obj["debug_dir"] = None

    # Set debug mode in context
    ctx.obj["debug"] = debug


autoraid.add_command(upgrade)
autoraid.add_command(network)


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
