"""PyInstaller entry point for the frozen Raid Autoupgrade exe.

A double-clicked exe receives no CLI subcommand, so this bypasses the Click
group in ``main.py`` and calls the GUI launcher directly. Elevation is handled
by the ``requireAdministrator`` manifest embedded via ``uac_admin`` in the
``.spec`` file — the runtime ShellExecuteW relaunch in ``main.py`` never fires
for the frozen build (it would re-extract the whole onefile bundle a second
time) and remains only for the ``uv run`` developer path.
"""

from raid_autoupgrade.gui.server import start


def main() -> None:
    start(debug=False)


if __name__ == "__main__":
    main()
