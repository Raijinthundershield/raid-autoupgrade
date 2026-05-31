# Raid Autoupgrade

A Windows desktop tool to automate the "airplane mode trick" for gear upgrades in Raid: Shadow Legends. Raid Autoupgrade uses computer vision to count failed upgrade attempts offline, then spends those attempts on another piece to save silver.

> **⚠️ WARNING**: This tool automates gameplay and **may violate Raid: Shadow Legends' Terms of Service**. Use at your own risk.

**New to the airplane mode trick?** See [How It Works](docs/airplane-mode-trick.md) for a detailed explanation.

## Download

Grab the latest `RaidAutoupgrade-v<version>-win64.exe` from the [**Releases
page**](../../releases/latest). The app asks for administrator rights at
launch (required for network-adapter control).

Because the exe is unsigned, your browser and Windows may flag it as unsafe when
you download or run it. See
[**Troubleshooting the download**](#troubleshooting-the-download) if any of them
stops you.

> **Building from source?** See [CONTRIBUTING.md](CONTRIBUTING.md) for prerequisites, setup, and the dev workflow.

## Usage

Once the app is running:

1. **Calibrate regions**:
   - Navigate to the upgrade screen of a gear piece in Raid
   - Open the **Calibration tab**, click **Capture Screenshot**, then draw regions over the upgrade progress bar and upgrade button (examples below). It is important that the progress bar region does not go beyond the black part.
   - Regions are saved and reused across sessions. You need to recalibrate if the window size changes.

   ![Region Selection](docs/images/image_with_regions.png)

2. **Select network adapters** (one-time):
   - In the **Run** tab, use the Network sidebar to choose which adapters to disable during counting (Wi-Fi, Ethernet, etc.). All adapters that provide network access need to be selected.

3. **Run an upgrade**:
   - Navigate to the upgrade screen of the gear piece to count fails on
   - In the **Count panel**, click **Start Count** — network is disabled automatically while counting
   - Navigate to the upgrade screen of the gear piece to spend upgrades on
   - In the **Spend panel**, click **Start Spend** — max attempts was auto-populated from the count
   - Enable **Continue upgrade** in the Spend panel for level 10 gear to upgrade to level 12 in case it upgrades to level 11 before max attempts is reached. By default it stops after one upgrade.

## Important Notes

- **Window size**: Keep the Raid window size constant during a session — regions are cached per window size, so resizing invalidates them and forces recalibration
- **Foreground window**: the Raid window activates and grabs focus during operation.
- **First-try success**: the tool may misbehave on upgrades that succeed on the very first attempt
- **App data location**: settings and debug captures live under `%PROGRAMDATA%\RaidAutoupgrade\`

## Troubleshooting the download

The downloaded exe is unsigned, so Windows treats it cautiously. Each of these is
expected.

- **Browser blocks the download** — your browser may flag the exe as unsafe and
  refuse to save it. Click **Keep** / **Keep anyway** in the download bar to get
  the file.
- **Microsoft Edge WebView2 runtime** — the app's window renders through it. It is
  preinstalled on current Windows 10/11; if it is missing the app opens the
  download page for you ([aka.ms/webview2](https://aka.ms/webview2)).
- **SmartScreen warning** — Windows shows a *"Windows protected your PC"* dialog on
  first run. Click **More info → Run anyway** to proceed.
- **Antivirus false positive** — Defender may flag the exe (e.g. `Trojan:...!ml`)
  and quarantine it. This is a known false positive for unsigned single-file
  PyInstaller apps; restore it via **Windows Security → Protection history →
  Restore** (or **Allow on device**). Full steps are in the Release notes.

If launch fails, the app writes a log to
`%PROGRAMDATA%\RaidAutoupgrade\logs\app.log` — include it when reporting issues.

## License & Disclaimer

**License**: Personal use only. See [LICENSE](LICENSE) for full terms.

**Legal**: See [DISCLAIMER.md](DISCLAIMER.md) for important legal information regarding use of this tool.
