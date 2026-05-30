# Raid Autoupgrade

A Windows desktop tool to automate the "airplane mode trick" for gear upgrades in Raid: Shadow Legends. Raid Autoupgrade uses computer vision to count failed upgrade attempts offline, then automatically spends those attempts on another piece to save silver.

> **⚠️ WARNING**: This tool automates gameplay and **may violate Raid: Shadow Legends' Terms of Service**. Use at your own risk. Read the full [DISCLAIMER](DISCLAIMER.md) before using.

**New to the airplane mode trick?** See [How It Works](docs/airplane-mode-trick.md) for a detailed explanation.

## Quick Start

### Download (no developer tools)

Most players want this path. Grab the latest `RaidAutoupgrade-v<version>-win64.exe`
from the [**Releases page**](../../releases/latest) and double-click it — no
Python, Node, or command line needed. The app asks for administrator rights once
at launch (required for network-adapter control).

Two things to expect on a fresh Windows machine:

- **Microsoft Edge WebView2 runtime** — the app's window renders through it. It
  is preinstalled on current Windows 10/11; if it is missing the app opens the
  download page for you ([aka.ms/webview2](https://aka.ms/webview2)).
- **SmartScreen warning** — the exe is unsigned, so Windows shows a *"Windows
  protected your PC"* dialog on first run. This is expected for a new unsigned
  app. Click **More info → Run anyway** to proceed.
- **Antivirus false positive** — Defender may flag the exe (e.g.
  `Trojan:...!ml`) and quarantine it. This is a known false positive for
  unsigned single-file PyInstaller apps; restore it via **Windows Security →
  Protection history → Restore** (or **Allow on device**). Full steps are in the
  Release notes.

If launch fails, the app writes a log to
`%PROGRAMDATA%\RaidAutoupgrade\logs\app.log` — include it when reporting issues.

### Prerequisites (from source)

- **Windows 10/11** (the tool uses WMI and Win32 APIs)
- **Administrator rights** (required for WMI network adapter control — the app prompts for elevation on launch)
- [**uv**](https://docs.astral.sh/uv/) for the Python side
- [**Node.js**](https://nodejs.org/) 20+ for building the frontend

### Setup (from source)

The desktop window renders the **built** React frontend served by the in-process FastAPI backend, so the frontend must be built before the first launch (and after any frontend change).

```bash
# 1. Install Python dependencies
uv sync

# 2. Build the frontend (produces frontend/dist/, which FastAPI serves)
cd frontend
npm install
npm run build
cd ..
```

### Run

1. **Launch the GUI**:
   ```bash
   uv run raid-autoupgrade gui
   ```
   On launch the app checks for admin rights and, if missing, prompts a UAC dialog to relaunch elevated.

   > **Developing the frontend?** Run the Vite dev server for hot-reload instead of rebuilding: in one terminal `cd frontend && npm run dev`, then in another `uv run raid-autoupgrade gui --dev`. The window points at the dev server, which proxies `/api` and `/ws` to the backend.

2. **Calibrate regions** (whenever the Raid window is resized):
   - Navigate to the upgrade screen in Raid
   - Open the **Calibration tab**, click **Capture Screenshot**, then draw regions over the upgrade progress bar and upgrade button
   - Regions are saved and reused across sessions — recalibrate if the window size changes

   ![Region Selection](docs/images/image_with_regions.png)

3. **Select network adapters** (one-time):
   - In the **Run tab**, use the Network sidebar to choose which adapters to disable during counting (Wi-Fi, Ethernet, etc.)

4. **Run an upgrade**:
   - Navigate to the upgrade screen of the gear piece to count fails on
   - In the **Count panel**, click **Start Count** — network is disabled automatically while counting
   - Navigate to the upgrade screen of the gear piece to spend upgrades on
   - In the **Spend panel**, click **Start Spend** — max attempts is auto-populated from the count
   - Enable **Continue upgrade** in the Spend panel for level 10 gear to upgrade to level 12 if required

## Important Notes

- **Window size**: Keep the Raid window size constant during a session — regions are cached per window size, so resizing invalidates them and forces recalibration
- **Foreground window**: the Raid window activates and grabs focus during operation
  - Don't multitask while the tool runs (it repeatedly takes focus for screenshots and clicks)
  - It may briefly minimize/restore the Raid window
- **First-try success**: the tool may misbehave on upgrades that succeed on the very first attempt
- **App data location**: settings and debug captures live under `%PROGRAMDATA%\RaidAutoupgrade\`; calibrated regions live under `%LOCALAPPDATA%\RaidAutoupgrade\regions`

## License & Disclaimer

**License**: Personal use only. See [LICENSE](LICENSE) for full terms.

**Legal**: See [DISCLAIMER.md](DISCLAIMER.md) for important legal information regarding use of this tool.
