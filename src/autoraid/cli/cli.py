from pathlib import Path
import click
from diskcache import Cache
from loguru import logger

from autoraid.cli.upgrade_cli import upgrade
from autoraid.cli.network_cli import network
from autoraid.container import Container


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

    # Custom format function to extract short module name
    def format_short_name(record):
        """Extract short module name (last component) from full module path."""
        module_name = record["name"].split(".")[-1]
        function_name = record["function"]
        record["extra"]["short_name"] = f"{module_name}.{function_name}"

    if debug:
        # DEBUG mode: detailed logging with timestamps, save to file
        debug_dir = cache_dir / "debug"
        debug_dir.mkdir(exist_ok=True)

        # Console output with timestamps and full module path
        logger.add(
            sink=lambda msg: click.echo(msg, err=True),
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="DEBUG",
            colorize=True,
        )

        # File output with full details
        logger.add(
            sink=debug_dir / "autoraid.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG",
            rotation="10 MB",
        )

        logger.debug(f"Debug mode enabled. Logging to {debug_dir / 'autoraid.log'}")
        ctx.obj["debug_dir"] = debug_dir
    else:
        # INFO mode: clean output with timestamps and short module.function names
        logger.add(
            sink=lambda msg: click.echo(msg, err=True),
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <cyan>{extra[short_name]: <35}</cyan> | <level>{message}</level>",
            level="INFO",
            colorize=True,
            filter=lambda record: format_short_name(record)
            or True,  # Patch each record
        )
        ctx.obj["debug_dir"] = None

    # Set debug mode in context
    ctx.obj["debug"] = debug


autoraid.add_command(upgrade)
autoraid.add_command(network)


@autoraid.command()
def gui():
    """Launch the native desktop GUI interface.

    Opens a native desktop window with a graphical interface for managing
    upgrade workflows, network adapters, and UI regions.
    """
    from autoraid.gui.app import main

    main()
