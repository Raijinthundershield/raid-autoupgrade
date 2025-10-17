# GUI Functional Specification: AutoRaid GUI

## Overview

A desktop GUI application that provides all the functionality of the existing CLI through a graphical interface. The GUI uses NiceGUI in native mode to create a Windows desktop application.

**Key Principles:**
- Transport existing CLI functionality to GUI controls
- NO new functionality beyond what CLI offers
- Images display via cv2.imshow windows (NOT embedded in GUI)
- Simple, functional interface focused on usability

## Main Window Layout

### Window Properties
- **Title**: AutoRaid - Raid: Shadow Legends Auto-Upgrade Tool
- **Size**: 800x700 pixels
- **Mode**: Native desktop window (not browser-based)

### Top Section: Settings
- **Debug Mode Toggle**: Checkbox to enable/disable debug mode
  - When enabled: Saves screenshots and metadata to cache directory
  - Status visible to user

### Middle Section: Tabbed Interface
Three tabs organize functionality:
1. **Upgrade Tab** - Count and spend upgrade operations
2. **Regions Tab** - Region management and selection
3. **Network Tab** - Network adapter control

### Bottom Section: Output Log
- Scrollable log area showing:
  - Operation status messages
  - Progress updates
  - Warnings and errors
  - Results from operations

---

## Tab 1: Upgrade Operations

### Section A: Count Upgrade Fails

**Purpose**: Count how many upgrade fails occur before success (airplane mode trick)

**Controls:**
- **Network Adapters** (Multi-select checkboxes):
  - Lists all available network adapters
  - Format: "Adapter Name (ID: X)"
  - User can select multiple adapters to disable during counting
  - Optional: If no adapters selected, user must manually use airplane mode

- **Start Count Button**:
  - Begins the counting operation
  - Disables selected network adapters
  - Monitors upgrade bar for fails
  - Displays count in log area
  - Re-enables network adapters when complete

- **Show Most Recent Gear Button**:
  - Opens cv2.imshow window displaying the last gear piece counted
  - Only enabled if a count operation has been completed
  - Shows cached screenshot

**User Flow:**
1. Select network adapters (optional)
2. Navigate to upgrade screen in Raid
3. Click "Start Count"
4. Wait for operation to complete
5. Review fail count in log

### Section B: Spend Upgrade Attempts

**Purpose**: Spend upgrade attempts up to a specified maximum with internet on

**Controls:**
- **Max Attempts** (Number input):
  - Required field
  - Min: 1, Max: 99
  - Specifies how many upgrade attempts to spend

- **Continue Upgrade Checkbox**:
  - Label: "Continue upgrade after reaching level 10"
  - Only use when the piece is at level 10 and you want to continue to level 11+

- **Start Spend Button**:
  - Begins the spend operation
  - Requires internet connectivity
  - Monitors upgrade bar and spends attempts
  - Stops at max attempts or successful upgrade
  - Displays results in log

**User Flow:**
1. Enter max attempts from count operation
2. Check continue upgrade if applicable
3. Ensure internet is connected
4. Navigate to upgrade screen in Raid
5. Click "Start Spend"
6. Monitor progress in log

---

## Tab 2: Region Management

### Section: Region Operations

**Purpose**: Manage cached UI regions for upgrade detection

**Status Display:**
- **Current Window Size**: Shows detected Raid window dimensions (e.g., "1920x1080")
- **Regions Cached**: Shows whether regions exist for current window size (✓ Yes / ✗ No)

**Controls:**
- **Show Regions Button**:
  - Opens cv2.imshow window showing screenshot with regions overlaid
  - Only works if regions are cached for current window size
  - Shows: upgrade bar, upgrade button, artifact icon

- **Force Manual Selection Checkbox**:
  - When checked: Always prompts for manual region selection
  - When unchecked: Uses cached regions if available

- **Select Regions Button**:
  - Launches region selection process
  - Auto-detects regions if "Force Manual Selection" is unchecked
  - Prompts for manual selection if auto-detect fails or checkbox is checked
  - Caches selected regions for current window size

- **Output Directory** (Text input + Browse button):
  - Optional path to save region data
  - Browse button opens file dialog

- **Show & Save Regions Button**:
  - Shows regions via cv2.imshow
  - Saves screenshot, regions JSON, and ROI images to output directory
  - Requires output directory to be specified

**User Flow (First Time Setup):**
1. Launch Raid and navigate to upgrade screen
2. Click "Select Regions"
3. Follow prompts to select upgrade bar, button, and artifact icon
4. Regions are cached for future use

**User Flow (View Regions):**
1. Click "Show Regions" to verify cached regions
2. Optionally specify output directory and click "Show & Save" to save data

---

## Tab 3: Network Management

### Section: Network Adapters

**Purpose**: Manage network adapters for the airplane mode trick

**Controls:**
- **Refresh Adapter List Button**:
  - Queries system for current network adapters
  - Updates adapter table and dropdown
  - Shows current enabled/disabled status

- **Adapter Table**:
  - Columns: ID, Name, Status, Type, Speed
  - Status shows: ✅ Enabled or ❌ Disabled
  - Speed shows: Mbps or "Unknown"
  - Read-only display

- **Select Adapter Dropdown**:
  - Lists all available adapters
  - Format: "ID - Adapter Name"
  - Used for individual enable/disable operations

- **Enable Button**:
  - Enables the selected adapter
  - Updates table status
  - Shows success/failure in log

- **Disable Button**:
  - Disables the selected adapter
  - Updates table status
  - Shows success/failure in log

**Note:**
- Multi-select for count/spend is in Upgrade tab
- This tab is for viewing and individual adapter control

**User Flow:**
1. Click "Refresh Adapter List" to see current adapters
2. Select an adapter from dropdown
3. Click "Enable" or "Disable" as needed
4. View result in log and table

---

## Settings (Global)

### Debug Mode

**Location**: Top of main window, always visible

**Control**: Checkbox labeled "Debug Mode"

**Behavior:**
- When enabled:
  - All operations save debug data to `cache-raid-autoupgrade/debug/`
  - Saves screenshots at each step
  - Saves region data
  - Saves metadata JSON files
  - Log shows debug directory path
- When disabled:
  - Normal operation, no debug data saved

**User Flow:**
1. Check "Debug Mode" before starting operations
2. Perform operations normally
3. Review debug data in cache directory after completion

---

## Output Log Area

### Purpose
Provide real-time feedback on all operations

### Display Content
- **Operation Start**: "Starting count operation..."
- **Progress Updates**: "Monitoring upgrade bar...", "Detected fail #3"
- **Network Status**: "Disabling adapter: WiFi (ID: 0)"
- **Results**: "Detected 7 fails. Stop reason: upgraded"
- **Warnings**: "No internet access detected. Aborting."
- **Errors**: "Raid window not found. Check if Raid is running."
- **Debug Info**: When debug mode enabled, shows save paths

### Behavior
- Auto-scrolls to latest message
- Maintains history for entire session
- Color-coded (if possible): info (white), warning (yellow), error (red)

---

## Error Handling and User Feedback

### Visual Notifications
- **Success**: Green notification toast
- **Error**: Red notification toast
- **Warning**: Yellow notification toast

### Common Error Scenarios

1. **Raid Window Not Found**:
   - Message: "Raid window not found. Check if Raid is running."
   - Action: User must launch Raid

2. **No Cached Regions**:
   - Message: "No cached regions found for current window size. Run region selection first."
   - Action: User must select regions

3. **Internet Required (Spend)**:
   - Message: "No internet access detected. Aborting."
   - Action: User must enable internet connection

4. **Internet Detected (Count)**:
   - Message: "Internet access detected and network id not specified. This will upgrade the piece. Aborting."
   - Action: User must select network adapters or manually disable internet

5. **Window Resized**:
   - Message: "Window size changed. Cached regions invalid. Please reselect regions."
   - Action: User must select regions again

6. **No Gear Cached**:
   - Message: "No gear piece has been counted yet. Aborting."
   - Action: User must run count operation first before showing gear

---

## Operational Constraints

### Requirements
- **Windows OS**: Required for network adapter control
- **Admin Rights**: Required if Raid is launched via RSLHelper
- **Raid Window**: Must be visible and accessible
- **Constant Window Size**: Raid window must not be resized during operations

### Limitations
- **First-Attempt Success**: Tool does not handle upgrades that succeed on first try
- **Network Control**: Only works with physical network adapters
- **Single Instance**: One operation at a time

---

## Success Criteria

The GUI is considered successful if:

1. ✅ All CLI functionality is accessible via GUI controls
2. ✅ Operations produce identical results to CLI commands
3. ✅ Images display via cv2.imshow (not embedded in GUI)
4. ✅ Debug mode works correctly
5. ✅ Network adapter control functions properly
6. ✅ Region selection and caching works
7. ✅ Error messages are clear and actionable
8. ✅ Log output provides adequate operation visibility
9. ✅ GUI remains responsive during operations
10. ✅ No new functionality beyond CLI is introduced
