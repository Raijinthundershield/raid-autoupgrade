import ctypes
import sys

import click


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def _prompt_relaunch_as_admin(extra_args: list[str]) -> None:
    """Show a native dialog and re-launch with UAC elevation if the user agrees."""
    IDYES = 6
    MB_YESNO = 0x00000004
    MB_ICONWARNING = 0x00000030
    MB_TOPMOST = 0x00040000

    result = ctypes.windll.user32.MessageBoxW(
        None,
        "Raid Autoupgrade requires administrator privileges to control network adapters.\n\nRestart as administrator?",
        "Administrator Required",
        MB_YESNO | MB_ICONWARNING | MB_TOPMOST,
    )
    if result == IDYES:
        # Re-launch the entry-point exe directly (sys.argv[0]) — not via the
        # interpreter — so the elevated process runs the same command.
        exe = sys.argv[0]
        args = ["gui"] + extra_args
        params = " ".join(f'"{a}"' for a in args)
        ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    sys.exit(0)


@click.group()
def raid_autoupgrade():
    """Raid Autoupgrade — Raid: Shadow Legends upgrade automation."""


@raid_autoupgrade.command()
@click.option("--debug", "-d", is_flag=True, default=False)
@click.option(
    "--dev", is_flag=True, default=False, help="Run against the Vite dev server."
)
def gui(debug: bool, dev: bool) -> None:
    """Launch the native desktop GUI."""
    import os

    if dev:
        os.environ["RAID_AUTOUPGRADE_DEV"] = "1"

    extra: list[str] = []
    if debug:
        extra.append("--debug")
    if dev:
        extra.append("--dev")

    if not _is_admin():
        _prompt_relaunch_as_admin(extra)

    from raid_autoupgrade.gui.server import start

    start(debug=debug)
