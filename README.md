# AutoRaid

A Windows desktop tool to automate the "airplane mode trick" for gear upgrades in Raid: Shadow Legends. AutoRaid uses computer vision to count failed upgrade attempts offline, then automatically spends those attempts on another piece to save silver.

> **⚠️ WARNING**: This tool automates gameplay and **may violate Raid: Shadow Legends' Terms of Service**. Use at your own risk. Read the full [DISCLAIMER](DISCLAIMER.md) before using.

**New to the airplane mode trick?** See [How It Works](docs/airplane-mode-trick.md) for a detailed explanation.

## Quick Start

1. **Launch the GUI**:
   ```bash
   uv run autoraid gui
   ```

2. **Setup** (one-time):
   - **Network Adapters**: Select which adapters to control turn off during counting (Wi-Fi, Ethernet, etc.)
   - **UI Regions**: Click "Select Regions" to select upgrade bar and button locations

3. **Workflow**:
   - Navigate to the upgrade screen of a gear piece we want to upgrade
   - **Count**: Click "Start Count" to count fails needed (network disabled automatically)
   - Navigate to the upgrade screen of a gear piece we will spend upgrades on
   - **Spend**: Click "Start Spend" to apply upgrades (max attempts auto-populated)
   - Enable "Continue Upgrade" for level 10 gear to upgrade to level 12 if required.

![Region Selection](docs/images/image_with_regions.png)

## Features

- **Automatic Network Management**: Disable/enable adapters automatically during count workflow
- **Computer Vision**: Auto-detect upgrade bar and button (currently not working), or select manually
- **Real-time Logs**: Live progress updates in GUI log panel
- **Persistent Settings**: Regions cached between sessions
- **Continue Mode**: Automatically continue upgrading level 10+ gear

## CLI Alternative

For advanced users, CLI commands are available:

```bash
# List network adapters
autoraid network list

# Count upgrade fails
autoraid upgrade count -n <adapter_ids>

# Spend upgrade attempts
autoraid upgrade spend --max-attempts <n_fails> [--continue-upgrade]

# Manage regions
autoraid upgrade region show          # View cached regions
autoraid upgrade region select [-m]   # Select regions (auto or manual)

# Debug mode
autoraid --debug <command>
```

## Important Notes

- **Windows only**: Uses WMI for network adapter control
- **Administrator rights**: Required if Raid is launched via RSLHelper
- **Window size**: Keep Raid window size constant (regions cached per window size)
- **Foreground window**: Raid window will activate and grab focus during operation
  - Hard multitask while tool is running (window repeatedly takes focus for screenshots and clicks)
  - May briefly minimize/restore
- **First-try success**: Tool might have issues with upgrades that succeed on first attempt
- **Cache folder**: Creates `cache-raid-autoupgrade/` in working directory

## Roadmap (slightly ordered)
* Fix automatic detection of progress bar and upgrade button
* Add automatic detection of piece level and whether it can continue to upgrade
   - lvl 10 -> continue upgrade
   - check to see if we spend upgrades on a piece with level <10 or >= 12
* Make it possible to have the raid window in the background.
    - Enable background screenshot
    - Enable background clicking

## License & Disclaimer

**License**: Personal use only. See [LICENSE](LICENSE) for full terms.

**Legal**: See [DISCLAIMER.md](DISCLAIMER.md) for important legal information regarding use of this tool.
