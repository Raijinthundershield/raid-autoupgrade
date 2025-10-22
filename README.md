# AutoRaid

The following tools are currently available:

`autoraid`: A command-line tool to help doing the "airplane" mode trick semi-automatically.
It can count failed upgrades as well as starting an upgrade and stop it after a
set amount of upgrade attempts.

## Usage

The tool provides several commands to help with upgrading equipment in Raid:

- `autoraid upgrade`: Commands for counting and spending upgrade attempts
- `autoraid network`: Commands for managing network adapters

### Counting upgrade attempts

To count the amount of fails we need to have internet turned off. This can be handled manually or automatically by the tool itself.


#### Counting upgrades

To count the number of fails needed to upgrade a piece:

1. Within Raid, go to the upgrade menu of the piece you want to test.

2. If using network management:
   ```bash
   autoraid upgrade count -n <adapter_ids>
   ```
   The tool will automatically disable the specified network adapters and turn them on again on exit.


3. If managing network manually:
   - Disable your network adapters first
   - Then run:
   ```bash
   autoraid upgrade count
   ```

4. The tool will try to detect the progress bar and the upgrade button, if not it will prompt you to select two regions (see example image below) :
   - First, select the upgrade bar region (only include the bar itself)
   - Then, select the upgrade button region

![alt text](docs/images/image_with_regions.png)

5. The tool will:
   - Start the upgrade process
   - Count the number of fails
   - Stop when it detects a successful upgrade
   - Re-enable network adapters if using network management

6. Note down the number of fails reported. You'll need this number when spending upgrade attempts.


You can view the most recent gear piece that was counted using the `-s` flag:
```bash
autoraid upgrade count -s
```
This will display an image of the gear piece that was last counted. This is useful for verifying which piece was being upgraded.

#### Getting network adapter id

To automatically manage network adapters, you need to get their IDs first:

1. Run the command:
```bash
autoraid network list
```

2. This will display a table showing all available network adapters with their:
   - ID
   - Name
   - Status - ✅ Enabled or ❌ Disabled
   - Type
   - Speed

3. Note down the IDs of the adapters you want to control. You'll need these for the `-n` option in the count command.

Example output:
```
Network Adapters
┌────┬────────────┬────────────┬────────────┬────────────┐
│ ID │ Name       │ Status     │ Type       │ Speed      │
├────┼────────────┼────────────┼────────────┼────────────┤
│ 1  │ Wi-Fi      │ ✅ Enabled │ Wireless   │ 866 Mbps   │
│ 2  │ Ethernet   │ ❌ Disabled│ Wired      │ 1000 Mbps  │
└────┴────────────┴────────────┴────────────┴────────────┘
```

In this example, you would use `-n 1 2` to control both the Wi-Fi and Ethernet adapters with the `count command`.

### Spending upgrade attempts

To spend upgrade attempts on a piece:

1. Make sure you have internet access enabled.

2. Within Raid, go to the upgrade menu of the piece you want to upgrade.

3. Run the command:
   ```bash
   autoraid upgrade spend --max-attempts <n_fails>
   ```
   Where `n_fails` is the number of fails you noted from the counting process.

   If you're upgrading a piece that is level 10 and want to continue spending attempts after an upgrade, use the `--continue-upgrade` flag:
   ```bash
   autoraid upgrade spend --max-attempts <n_fails> --continue-upgrade
   ```
   This will continue spending upgrade attempts until the piece upgrades to level 12.

4. The tool will:
   - Start the upgrade process
   - Count the number of fails
   - Cancel the upgrade if max attempts is reached

Note: The tool will automatically use the cached regions. If there are no cached regions or the raid window size has changed, it will prompt for selection of new regions.

### Reviewing and selecting regions

You can review and manage the regions used for upgrade bar and button detection:

1. To view the currently cached regions:
   ```bash
   autoraid upgrade region show
   ```
   This will display an image with the cached regions highlighted. You can save this image by adding the `-s` flag:
   ```bash
   autoraid upgrade region show -s
   ```

2. To select new regions:
   ```bash
   autoraid upgrade region select
   ```
   This will prompt you to:
   - Select the upgrade bar region (only include the bar itself)
   - Select the upgrade button region

   You can also force manual selection even if regions are cached by using the `-m` flag:
   ```bash
   autoraid upgrade region select -m
   ```

The regions selected here will be cached and used with the other commands.

### Debug Mode

You can enable debug mode to save screenshots and other debugging information:

```bash
autoraid --debug <command>
```

This will save additional information to a `debug` directory within the cache folder.

## Limitations and Considerations
* Does not handle if there is an upgrade attempt on first try!
* Windows only
* The raid window will force itself to the foreground. This makes working on something on the same monitor a bit difficult.
* If you are running RSLHelper you need to run the script as administrator. This is due to raid being started as administrator.
* While the command runs make sure not to change the window size of the raid application.
* A cache folder will be generated in the folder in which the command is called.


## GUI Usage

### GUI Workflow Example

1. **Launch the GUI**: `uv run autoraid gui`

2. **Select Network Adapters** (scroll to Network Adapters section):
   - Check the boxes for the adapters you want to control (e.g., Wi-Fi, Ethernet)
   - Selection persists across application restarts

3. **Select UI Regions** (Region Management section):
   - Click "Select Regions (Auto)" to let the tool detect regions automatically
   - Or click "Select Regions (Manual)" to manually select upgrade bar and button
   - Click "Show Regions" to verify the cached regions

4. **Count Upgrade Fails** (Upgrade Workflows section):
   - In Raid, navigate to the upgrade screen for your gear piece
   - Click "Start Count" in the GUI
   - The tool will disable your selected network adapters, count fails, and re-enable adapters
   - View logs in the Live Logs section

5. **Spend Upgrade Attempts**:
   - The "Max Attempts" field will be auto-populated with your count result
   - Enable "Continue Upgrade" if upgrading level 10 gear
   - Click "Start Spend" to automatically spend attempts

Cached regions are stored in the same disk cache used by the CLI (`cache-raid-autoupgrade/` directory).

## Roadmap (slightly ordered)
* Add automatic detection of piece level and whether it can continue to upgrade
   - lvl 10 -> continue upgrade
   - check to see if we spend upgrades on a piece with level <10 or >= 12
* Make it possible to have the raid window in the background.
    - Enable background screenshot
    - Enable background clicking
