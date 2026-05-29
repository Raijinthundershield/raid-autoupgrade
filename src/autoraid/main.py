import ctypes
import sys

import click


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def _prompt_relaunch_as_admin() -> None:
    """Show a native dialog and re-launch with UAC elevation if the user agrees."""
    IDYES = 6
    MB_YESNO = 0x00000004
    MB_ICONWARNING = 0x00000030
    MB_TOPMOST = 0x00040000

    result = ctypes.windll.user32.MessageBoxW(
        None,
        "AutoRaid requires administrator privileges to control network adapters.\n\nRestart as administrator?",
        "Administrator Required",
        MB_YESNO | MB_ICONWARNING | MB_TOPMOST,
    )
    if result == IDYES:
        params = " ".join(f'"{a}"' for a in sys.argv)
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1
        )
    sys.exit(0)


@click.group()
def autoraid():
    """AutoRaid — Raid: Shadow Legends upgrade automation."""


@autoraid.command()
@click.option("--debug", "-d", is_flag=True, default=False)
def gui(debug: bool):
    """Launch the native desktop GUI."""
    if not _is_admin():
        _prompt_relaunch_as_admin()

    from autoraid.gui.server import start

    start(debug=debug)
