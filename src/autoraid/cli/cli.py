from pathlib import Path
import click
from diskcache import Cache
from loguru import logger

from autoraid.cli.upgrade_cli import upgrade
from autoraid.cli.network_cli import network


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

    # Store cache in context
    ctx = click.get_current_context()
    ctx.obj = {"cache": cache, "cache_dir": cache_dir}

    # Set debug mode
    ctx.obj["debug"] = debug
    ctx.obj["debug_dir"] = None
    if debug:
        debug_dir = cache_dir / "debug"
        debug_dir.mkdir(exist_ok=True)
        logger.debug(
            f"Debug mode enabled. Saving screenshots and other information to {debug_dir}"
        )
        ctx.obj["debug_dir"] = debug_dir


autoraid.add_command(upgrade)
autoraid.add_command(network)
