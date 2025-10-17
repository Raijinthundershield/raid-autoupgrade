# GUI Conversion Plan: NiceGUI Native Mode

## Overview

Convert the existing CLI application to a GUI application using NiceGUI in native mode. This conversion will:
- Transport all existing CLI functionality to GUI controls
- NOT add any new functionality
- Keep cv2.imshow for image display (no images in the GUI)
- Only have controls (buttons, inputs, checkboxes, etc.) in the GUI
- Use NiceGUI's native mode to create a desktop application window

## Architecture

### File Structure

```
src/autoraid/
├── gui/
│   ├── __init__.py              # Empty init file
│   ├── main.py                  # Main GUI entry point with NiceGUI app
│   ├── components/
│   │   ├── __init__.py          # Empty init file
│   │   ├── upgrade_tab.py       # Upgrade operations UI
│   │   ├── region_tab.py        # Region management UI
│   │   ├── network_tab.py       # Network adapter management UI
│   │   └── settings.py          # Debug settings UI component
│   └── state.py                 # Application state management
├── cli/                         # Existing CLI (keep as-is)
├── autoupgrade/                 # Existing logic (keep as-is)
└── ...                          # Other existing modules
```

## Dependencies

### Add to pyproject.toml

```toml
dependencies = [
    # ... existing dependencies ...
    "nicegui>=1.4.0",
]
```

## GUI Layout

### Main Window Structure

```
┌─────────────────────────────────────────────────────┐
│ AutoRaid - Raid: Shadow Legends Auto-Upgrade Tool  │
├─────────────────────────────────────────────────────┤
│ [Debug Mode: ☐ Enabled]                            │
├─────────────────────────────────────────────────────┤
│ ┌─ Tabs ───────────────────────────────────────┐   │
│ │ [Upgrade] [Regions] [Network]                │   │
│ └──────────────────────────────────────────────┘   │
│                                                     │
│ [Tab Content Area - see details below]             │
│                                                     │
│ [Status/Log Output Area]                           │
└─────────────────────────────────────────────────────┘
```

### Tab 1: Upgrade Operations

Maps to `upgrade` CLI commands:

```
┌─ Count Upgrade Fails ──────────────────────────┐
│                                                │
│ Network Adapters (multi-select):              │
│ ☐ Adapter 1 (ID: 0)                          │
│ ☐ Adapter 2 (ID: 1)                          │
│ ...                                           │
│                                                │
│ [Start Count] [Show Most Recent Gear]         │
└────────────────────────────────────────────────┘

┌─ Spend Upgrade Attempts ───────────────────────┐
│                                                │
│ Max Attempts: [____] (required)                │
│                                                │
│ ☐ Continue upgrade after reaching level 10    │
│                                                │
│ [Start Spend]                                  │
└────────────────────────────────────────────────┘
```

**Functionality:**
- `upgrade count` command:
  - Multi-select checkboxes for network adapters
  - "Start Count" button executes count operation
  - "Show Most Recent Gear" button displays cached gear via cv2.imshow
- `upgrade spend` command:
  - Number input for max attempts
  - Checkbox for continue-upgrade flag
  - "Start Spend" button executes spend operation

### Tab 2: Region Management

Maps to `upgrade region` CLI commands:

```
┌─ Region Operations ────────────────────────────┐
│                                                │
│ Current Window Size: 1920x1080                │
│ Regions Cached: ✓ Yes / ✗ No                 │
│                                                │
│ [Show Regions]                                 │
│                                                │
│ ☐ Force manual selection                      │
│ [Select Regions]                               │
│                                                │
│ Save output:                                   │
│ Output Directory: [_______________] [Browse]   │
│ [Show & Save Regions]                          │
└────────────────────────────────────────────────┘
```

**Functionality:**
- `upgrade region show` command:
  - Display current window size and cache status
  - "Show Regions" button shows regions via cv2.imshow
  - Optional output directory for saving
  - "Show & Save Regions" button shows and saves to directory
- `upgrade region select` command:
  - Checkbox for manual selection flag
  - "Select Regions" button launches region selection

### Tab 3: Network Management

Maps to `network` CLI commands:

```
┌─ Network Adapters ─────────────────────────────┐
│                                                │
│ [Refresh Adapter List]                         │
│                                                │
│ Available Adapters:                            │
│ ┌──────────────────────────────────────────┐  │
│ │ ID | Name          | Status   | Type    │  │
│ │ 0  | WiFi          | ✅ Enabled | 802.11 │  │
│ │ 1  | Ethernet      | ❌ Disabled| Ethernet│ │
│ │ ...                                      │  │
│ └──────────────────────────────────────────┘  │
│                                                │
│ Select Adapter: [Dropdown ▼]                  │
│                                                │
│ [Enable] [Disable]                             │
│                                                │
│ Or use multi-select above for count/spend     │
└────────────────────────────────────────────────┘
```

**Functionality:**
- `network list` command:
  - "Refresh" button updates adapter list
  - Table display of all adapters (ID, Name, Status, Type, Speed)
- `network enable/disable` commands:
  - Dropdown to select specific adapter
  - "Enable" and "Disable" buttons for selected adapter

### Debug Settings (Always Visible at Top)

Maps to `--debug` flag:

```
┌─ Settings ─────────────────────────────────────┐
│ ☐ Debug Mode                                   │
│   (Saves screenshots and metadata to cache)    │
└────────────────────────────────────────────────┘
```

## Implementation Details

### 1. Application State Management (state.py)

```python
class AppState:
    def __init__(self):
        self.cache = None  # diskcache.Cache instance
        self.cache_dir = Path("cache-raid-autoupgrade")
        self.debug = False
        self.debug_dir = None
        self.network_manager = NetworkManager()

    def toggle_debug(self, enabled: bool):
        # Update debug state

    def get_network_adapters(self) -> list[NetworkAdapter]:
        # Get adapters from network manager
```

### 2. Main GUI Entry Point (main.py)

```python
from nicegui import ui, app
from autoraid.gui.state import AppState
from autoraid.gui.components.upgrade_tab import create_upgrade_tab
from autoraid.gui.components.region_tab import create_region_tab
from autoraid.gui.components.network_tab import create_network_tab
from autoraid.gui.components.settings import create_settings_section

def main():
    # Initialize app state
    state = AppState()

    # Create main UI
    with ui.header():
        ui.label('AutoRaid - Raid: Shadow Legends Auto-Upgrade Tool')

    # Debug settings at top
    create_settings_section(state)

    # Create tabs
    with ui.tabs() as tabs:
        upgrade_tab = ui.tab('Upgrade')
        region_tab = ui.tab('Regions')
        network_tab = ui.tab('Network')

    with ui.tab_panels(tabs, value=upgrade_tab):
        with ui.tab_panel(upgrade_tab):
            create_upgrade_tab(state)
        with ui.tab_panel(region_tab):
            create_region_tab(state)
        with ui.tab_panel(network_tab):
            create_network_tab(state)

    # Status/log output area
    ui.separator()
    ui.label('Output:')
    log_output = ui.log().classes('w-full h-40')

    # Run in native mode
    ui.run(native=True, window_size=(800, 700), title='AutoRaid')

if __name__ in {"__main__", "__mp_main__"}:
    main()
```

### 3. Upgrade Tab Component (upgrade_tab.py)

```python
def create_upgrade_tab(state: AppState):
    # Count section
    with ui.card().classes('w-full'):
        ui.label('Count Upgrade Fails').classes('text-h6')

        # Network adapter selection
        ui.label('Network Adapters (for airplane mode):')
        adapter_checkboxes = []
        adapters = state.get_network_adapters()
        for adapter in adapters:
            checkbox = ui.checkbox(f'{adapter.name} (ID: {adapter.id})')
            adapter_checkboxes.append((checkbox, adapter.id))

        with ui.row():
            ui.button('Start Count', on_click=lambda: start_count(state, adapter_checkboxes))
            ui.button('Show Most Recent Gear', on_click=lambda: show_recent_gear(state))

    # Spend section
    with ui.card().classes('w-full'):
        ui.label('Spend Upgrade Attempts').classes('text-h6')

        max_attempts = ui.number('Max Attempts', value=0, min=1, max=99)
        continue_upgrade = ui.checkbox('Continue upgrade after reaching level 10')

        ui.button('Start Spend', on_click=lambda: start_spend(
            state, max_attempts.value, continue_upgrade.value
        ))

def start_count(state, adapter_checkboxes):
    # Extract selected adapter IDs
    selected_ids = [aid for cb, aid in adapter_checkboxes if cb.value]
    # Call existing count logic from upgrade_cli.py
    # Show output in log area

def show_recent_gear(state):
    # Call existing show-most-recent-gear logic
    # Display via cv2.imshow

def start_spend(state, max_attempts, continue_upgrade):
    # Call existing spend logic from upgrade_cli.py
```

### 4. Region Tab Component (region_tab.py)

```python
def create_region_tab(state: AppState):
    with ui.card().classes('w-full'):
        ui.label('Region Operations').classes('text-h6')

        # Status display
        status_label = ui.label('Checking window...')

        ui.button('Show Regions', on_click=lambda: show_regions(state))

        manual_select = ui.checkbox('Force manual selection')
        ui.button('Select Regions', on_click=lambda: select_regions(
            state, manual_select.value
        ))

        ui.separator()
        ui.label('Save output:')
        output_dir = ui.input('Output Directory', placeholder='/path/to/dir')
        ui.button('Browse', on_click=lambda: browse_directory(output_dir))
        ui.button('Show & Save Regions', on_click=lambda: show_and_save_regions(
            state, output_dir.value
        ))

def show_regions(state):
    # Call existing region show logic
    # Display via cv2.imshow

def select_regions(state, manual: bool):
    # Call existing region select logic

def show_and_save_regions(state, output_dir):
    # Call existing region show with --output-dir
```

### 5. Network Tab Component (network_tab.py)

```python
def create_network_tab(state: AppState):
    with ui.card().classes('w-full'):
        ui.label('Network Adapters').classes('text-h6')

        # Adapter table
        adapter_table = create_adapter_table(state)

        ui.button('Refresh Adapter List', on_click=lambda: refresh_adapters(
            adapter_table, state
        ))

        # Adapter selection and control
        adapter_select = ui.select(
            label='Select Adapter',
            options=[],  # Populated by refresh
            value=None
        )

        with ui.row():
            ui.button('Enable', on_click=lambda: toggle_adapter(
                state, adapter_select.value, True
            ))
            ui.button('Disable', on_click=lambda: toggle_adapter(
                state, adapter_select.value, False
            ))

def create_adapter_table(state):
    # Create table with columns: ID, Name, Status, Type, Speed
    # Return table reference for updates

def refresh_adapters(table, state):
    # Refresh adapter list in table and dropdown

def toggle_adapter(state, adapter_id, enable: bool):
    # Call network manager to enable/disable adapter
```

### 6. Settings Component (settings.py)

```python
def create_settings_section(state: AppState):
    with ui.card().classes('w-full'):
        ui.label('Settings').classes('text-h6')

        debug_checkbox = ui.checkbox('Debug Mode')
        debug_checkbox.on_value_change(lambda e: state.toggle_debug(e.value))
        ui.label('(Saves screenshots and metadata to cache directory)')
```

## Key Implementation Principles

### 1. Reuse Existing Logic

All core functionality should call existing functions from:
- `autoraid.autoupgrade.autoupgrade`
- `autoraid.network`
- `autoraid.interaction`

The GUI is just a thin wrapper that:
- Collects user input from controls
- Calls existing functions with appropriate parameters
- Displays results in log area or via cv2.imshow

### 2. Threading for Long Operations

Count and spend operations are long-running. Use threading to prevent GUI freeze:

```python
import threading

def start_count_thread(state, adapter_ids):
    def run():
        # Call count_upgrade_fails from autoupgrade module
        # Update GUI with results

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
```

Or use NiceGUI's built-in async support:

```python
async def start_count_async(state, adapter_ids):
    # Use asyncio.to_thread or run_in_executor
    result = await asyncio.to_thread(count_upgrade_fails, ...)
```

### 3. Logging Integration

Redirect loguru logs to GUI log area:

```python
from loguru import logger
from nicegui import ui

log_display = ui.log()

# Add custom handler
logger.add(lambda msg: log_display.push(msg), format="{message}")
```

### 4. Error Handling

All button click handlers should wrap operations in try/except:

```python
def start_count_handler():
    try:
        # Operation logic
    except Exception as e:
        logger.error(f"Error during count: {e}")
        ui.notify(f"Error: {e}", type='negative')
```

## Entry Point Configuration

### Update pyproject.toml

Add new GUI entry point:

```toml
[project.scripts]
autoraid = "autoraid.cli.cli:autoraid"  # Existing CLI
autoraid-gui = "autoraid.gui.main:main"  # New GUI
```

Users can run:
- `autoraid` for CLI mode (unchanged)
- `autoraid-gui` for GUI mode (new)

## Testing Strategy

1. **Manual Testing**: Test each GUI control maps to correct CLI command
2. **Functional Testing**: Verify all operations work identically to CLI
3. **State Testing**: Ensure app state (debug, cache, network) is maintained correctly

## Migration Notes

### What Changes
- New entry point: `autoraid-gui`
- New dependency: nicegui
- New directory: `src/autoraid/gui/`

### What Stays the Same
- All existing CLI commands (unchanged)
- All core logic in autoupgrade, network, interaction modules
- All cv2.imshow calls for image display
- Cache management
- Network adapter control

### What is NOT Changed
- No new functionality added
- No changes to existing modules outside of `gui/`
- No changes to how images are displayed (still cv2.imshow)
- No integration of images into GUI

## Rollout Steps

1. Add NiceGUI dependency to pyproject.toml
2. Create `src/autoraid/gui/` directory structure
3. Implement state.py for app state management
4. Implement settings.py for debug toggle
5. Implement network_tab.py (simplest, good starting point)
6. Implement region_tab.py
7. Implement upgrade_tab.py (most complex)
8. Implement main.py to tie everything together
9. Add autoraid-gui entry point to pyproject.toml
10. Test all functionality end-to-end
11. Update README with GUI usage instructions

## Success Criteria

- [ ] GUI launches via `autoraid-gui` command
- [ ] All CLI functionality accessible via GUI controls
- [ ] Debug mode toggle works and affects operations
- [ ] Count operation correctly controls network and counts fails
- [ ] Spend operation correctly spends attempts with max limit
- [ ] Region show/select work with manual flag
- [ ] Network adapter list/enable/disable work
- [ ] All images display via cv2.imshow (not in GUI)
- [ ] Logs appear in GUI output area
- [ ] No new functionality added beyond GUI controls
- [ ] Existing CLI remains unchanged and functional

## Notes

- NiceGUI native mode creates a Chromium-based window, but looks like a desktop app
- All heavy computation should be in separate threads to keep GUI responsive
- Keep GUI simple and functional - no fancy styling needed for v1
- Focus on exact CLI-to-GUI parity, not enhancement
