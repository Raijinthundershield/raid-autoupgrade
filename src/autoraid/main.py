import click


@click.group()
def autoraid():
    """AutoRaid — Raid: Shadow Legends upgrade automation."""


@autoraid.command()
@click.option("--debug", "-d", is_flag=True, default=False)
def gui(debug: bool):
    """Launch the native desktop GUI."""
    from autoraid.gui.server import start

    start(debug=debug)
