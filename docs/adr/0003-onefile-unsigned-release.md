---
status: accepted
---

# Ship a one-file, unsigned PyInstaller exe via GitHub Releases

We package the app as a single PyInstaller `--onefile` Windows `.exe`, **unsigned**,
built on `windows-latest` and attached to a GitHub Release on `v*` tag push, so a
user can download one file and double-click it. We accept onefile's slow first
launch (the ~150MB CV/WebView bundle unpacks to `%TEMP%` each run) and unsigned's
SmartScreen/antivirus friction as the price of download simplicity, over a
folder-zip (needs an unzip step) or an installer (needs an install step and more
CI tooling), and over a signing certificate (recurring cost + identity vetting we
don't want for a hobby tool). The exe embeds a `requireAdministrator` UAC manifest
(`--uac-admin`) so it elevates with one prompt at launch rather than the runtime
MessageBox+`ShellExecuteW` relaunch, which under onefile would re-extract the whole
bundle a second time.

## Considered options

- **One-file unsigned exe (chosen)** — truest match for "download and double-click."
  Cost: slow first launch, SmartScreen "Windows protected your PC" wall, elevated
  antivirus false-positive odds, and "Unknown publisher" on the UAC prompt. All are
  UX/trust friction, not functional loss; documented in the Release notes.
- **One-folder zip** — fast startup, far fewer AV false positives. Rejected: forces
  an unzip step before the double-click.
- **Installer (Inno Setup)** — Start Menu shortcut, clean uninstall, in-manifest
  admin. Rejected for v1: extra CI tooling and an install step.
- **Code signing** — would soften SmartScreen (instantly with EV) and reduce AV
  friction. Rejected: cert cost (~$200–400/yr for EV) and identity vetting aren't
  worth it for current distribution scale.

## Consequences

- **Elevation:** the frozen exe never runs the `main.py` relaunch path — the
  manifest handles it. That path stays only for the `uv run` dev flow.
- **Entry point:** double-click passes no CLI args, so the build targets a dedicated
  `packaging/entry.py → gui.server.start(debug=False)`, bypassing the Click group.
- **Frozen assets:** `frontend/dist` (gitignored, built in CI) is bundled as data,
  and `server.py` must resolve it via `sys._MEIPASS` when `sys.frozen`, else the
  source-relative path. This is a prerequisite, not optional — the current
  `__file__`-relative path does not survive freezing.
- **Diagnostics:** a `--windowed` build discards stderr, so the app gains a rotating
  file log (`%PROGRAMDATA%\RaidAutoupgrade\logs\app.log`) and a fatal-startup
  MessageBox; a missing WebView2 runtime is detected up front and sent to
  `aka.ms/webview2` rather than crashing silently.
- **No CI smoke test:** launching needs WebView2, admin, and a real display, so CI
  verifies only that the build succeeds and the artifact exists. First-run
  validation stays manual on a Windows machine.
- **Version honesty:** the workflow fails if the `v*` tag and `pyproject.toml`
  version disagree, forcing a deliberate bump before each release.
