# AutoRaid

The following tools are currently available:

`raid_autoupgrade`: A command-line tool to help doing the "airplane" mode trick semi-automatically.
It can count failed upgrades as well as starting an upgrade and stop it after a
set amount of upgrade attempts.

## Usage

There are two main commands `raid-autoupgrade count` and `raid-autoupgrade
upgrade`. The former is used to count the amount of upgrade attempts that is
required to upgrade a piece, while the latter will spend upgrade attempts.


### Counting upgrade attempts

To count the amount of fails we need to have internet turned off. This can be handled manually or automatically by the tool itself.

#### Getting network adapter id

To automatically manage network adapters, you need to get their IDs first:

1. Run the command:
```bash
raid-autoupgrade network list
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

#### Counting upgrades

To count the number of fails needed to upgrade a piece:

1. Within Raid, go to the upgrade menu of the piece you want to test.

2. If using network management:
   ```bash
   raid-autoupgrade count -n <adapter_ids>
   ```
   The tool will automatically disable the specified network adapters.

3. If managing network manually:
   - Disable your network adapters first
   - Then run:
   ```bash
   raid-autoupgrade count
   ```

4. The tool will prompt you to select two regions (see example image below) :
   - First, select the upgrade bar region (only include the bar itself)
   - Then, select the upgrade button region

![alt text](docs/images/image_with_regions.png)

5. The tool will:
   - Start the upgrade process
   - Count the number of fails
   - Stop when it detects a successful upgrade
   - Re-enable network adapters if using network management

6. Note down the number of fails reported. You'll need this number when spending upgrade attempts.


### Spending upgrade attempts

To spend upgrade attempts on a piece:

1. Make sure you have internet access enabled.

2. Within Raid, go to the upgrade menu of the piece you want to upgrade.

3. Run the command:
   ```bash
   raid-autoupgrade upgrade --max-attempts <n_fails>
   ```
   Where `n_fails` is the number of fails you noted from the counting process.

   If you're upgrading a piece that is level 10 and want to continue spending attempts after an upgrade, use the `--continue-upgrade` flag:
   ```bash
   raid-autoupgrade upgrade --max-attempts <n_fails> --continue-upgrade
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
   raid-autoupgrade show-regions
   ```
   This will display an image with the cached regions highlighted. You can save this image by adding the `-s` flag:
   ```bash
   raid-autoupgrade show-regions -s
   ```

2. To select new regions manuallt:
   ```bash
   raid-autoupgrade select-regions
   ```
   This will prompt you to:
   - Select the upgrade bar region (only include the bar itself)
   - Select the upgrade button region

The regions selected here will be cached and used with the other commands.



## Limitations and Considerations
* Does not handle if there is an upgrade attempt on first try!
* Windows only
* The raid window will force itself to the foreground. This makes working on something on the same monitor a bit difficult.
* If you are running RSLHelper you need to run the script as administrator. This is due to raid being started as administrator.
* While the command runs make sure not to change the window size of the raid application.
* A cache folder will be generated in the folder in which the command is called.


## Roadmap (slightly ordered)
* Use `pyautogui.locateCenterOnScreen` to find upgrade bar and upgrade button instead of manual input.
* Take screenshot of the last piece a count was done for and add command to show it.
* Create GUI for autoupgrade.
* Create an autobattle tool that allows to create rules for battles.
* Make it possible to have the raid window in the background.
    - Enable background screenshot
    - Enable background clicking
