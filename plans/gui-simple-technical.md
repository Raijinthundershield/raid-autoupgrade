# GUI Technical Implementation: AutoRaid GUI

## Overview

Technical specification for implementing a NiceGUI-based desktop application that wraps the existing CLI functionality.

**Core Principle**: The GUI is a thin presentation layer that calls existing business logic. No duplication of functionality.

---

## Technology Stack

### Primary Framework
- **NiceGUI >= 1.4.0**: Web-based UI framework running in native mode
  - Uses Chromium to render UI in a desktop window
  - Python-based declarative UI construction
  - Built-in async support for non-blocking operations

### Existing Dependencies (Reused)
- **diskcache**: Cache management
- **loguru**: Logging
- **wmi**: Windows network adapter control
- **rich**: Table formatting (for network adapter display)
- **opencv-python**: Image display via cv2.imshow
- **pyautogui, pygetwindow**: Window interaction

---

## Project Structure

```
src/autoraid/
├── gui/
│   ├── __init__.py              # Empty init
│   ├── main.py                  # Entry point, main UI assembly
│   ├── state.py                 # Application state management
│   ├── components/
│   │   ├── __init__.py          # Empty init
│   │   ├── settings.py          # Debug settings component
│   │   ├── upgrade_tab.py       # Upgrade operations UI
│   │   ├── region_tab.py        # Region management UI
│   │   └── network_tab.py       # Network adapter management UI
│   └── utils.py                 # GUI-specific utilities (logging, threading)
├── cli/                         # Existing CLI (unchanged)
├── autoupgrade/                 # Existing logic (unchanged)
├── network.py                   # Existing logic (unchanged)
└── ...                          # Other existing modules (unchanged)
```

---

## Module Specifications

### 1. state.py - Application State Management

**Purpose**: Centralize application state and provide interface to backend modules

```python
from pathlib import Path
from diskcache import Cache
from autoraid.network import NetworkManager

class AppState:
    """Global application state shared across all GUI components"""

    def __init__(self):
        # Cache management
        self.cache_dir = Path("cache-raid-autoupgrade")
        self.cache_dir.mkdir(exist_ok=True)
        self.cache = Cache(str(self.cache_dir))

        # Debug settings
        self.debug = False
        self.debug_dir = None

        # Network manager
        self.network_manager = NetworkManager()

    def toggle_debug(self, enabled: bool) -> None:
        """Enable/disable debug mode"""
        self.debug = enabled
        if enabled:
            self.debug_dir = self.cache_dir / "debug"
            self.debug_dir.mkdir(exist_ok=True)
        else:
            self.debug_dir = None

    def get_context_dict(self) -> dict:
        """Return context dict compatible with CLI context object"""
        return {
            "cache": self.cache,
            "cache_dir": self.cache_dir,
            "debug": self.debug,
            "debug_dir": self.debug_dir,
        }
```

**Key Design:**
- Single instance shared across all components
- Matches CLI context structure for compatibility
- Provides `get_context_dict()` for passing to existing functions

---

### 2. main.py - Application Entry Point

**Purpose**: Construct main UI and run NiceGUI in native mode

```python
from nicegui import ui, app
from pathlib import Path
import sys

from autoraid.gui.state import AppState
from autoraid.gui.components.settings import create_settings_section
from autoraid.gui.components.upgrade_tab import create_upgrade_tab
from autoraid.gui.components.region_tab import create_region_tab
from autoraid.gui.components.network_tab import create_network_tab
from autoraid.gui.utils import setup_logging

def main():
    """Main entry point for GUI application"""

    # Initialize application state
    state = AppState()

    # Setup logging to GUI
    log_display = ui.log().classes('w-full h-40')
    setup_logging(log_display)

    # Header
    with ui.header().classes('items-center justify-between'):
        ui.label('AutoRaid - Raid: Shadow Legends Auto-Upgrade Tool').classes('text-h5')

    # Settings section (always visible)
    create_settings_section(state)

    ui.separator()

    # Main tabbed interface
    with ui.tabs().classes('w-full') as tabs:
        upgrade_tab = ui.tab('Upgrade')
        region_tab = ui.tab('Regions')
        network_tab = ui.tab('Network')

    with ui.tab_panels(tabs, value=upgrade_tab).classes('w-full'):
        with ui.tab_panel(upgrade_tab):
            create_upgrade_tab(state)

        with ui.tab_panel(region_tab):
            create_region_tab(state)

        with ui.tab_panel(network_tab):
            create_network_tab(state)

    # Output log section
    ui.separator()
    ui.label('Output Log:').classes('text-subtitle1')
    ui.label('(Note: Images will open in separate cv2 windows)').classes('text-caption')

    # Run in native mode
    ui.run(
        native=True,
        window_size=(800, 700),
        title='AutoRaid',
        reload=False,
    )

if __name__ in {"__main__", "__mp_main__"}:
    main()
```

**Key Implementation Details:**
- `ui.run(native=True)`: Creates standalone desktop window
- `window_size=(800, 700)`: Fixed initial size
- `reload=False`: Disable auto-reload for production
- Log display created early for logging setup

---

### 3. components/settings.py - Debug Settings

**Purpose**: Global settings UI component

```python
from nicegui import ui
from autoraid.gui.state import AppState

def create_settings_section(state: AppState) -> None:
    """Create debug settings section"""

    with ui.card().classes('w-full'):
        ui.label('Settings').classes('text-subtitle1')

        debug_checkbox = ui.checkbox('Debug Mode')
        debug_checkbox.on('update:model-value', lambda e: state.toggle_debug(e.args))

        ui.label(
            'When enabled, saves screenshots and metadata to cache directory'
        ).classes('text-caption')
```

**Key Features:**
- Updates `AppState.debug` on toggle
- Simple on/off control

---

### 4. components/upgrade_tab.py - Upgrade Operations

**Purpose**: Count and spend operations UI

**High-Level Structure:**
```python
from nicegui import ui
import asyncio
from loguru import logger

from autoraid.gui.state import AppState
from autoraid.autoupgrade.autoupgrade import count_upgrade_fails, StopCountReason
from autoraid.interaction import (
    window_exists, take_screenshot_of_window, click_region_center
)
from autoraid.autoupgrade.autoupgrade import get_regions
import cv2

def create_upgrade_tab(state: AppState) -> None:
    """Create upgrade operations tab"""

    # Count section
    with ui.card().classes('w-full'):
        ui.label('Count Upgrade Fails').classes('text-h6')

        ui.label('Network Adapters (for airplane mode):').classes('text-subtitle2')

        # Get adapters and create checkboxes
        adapter_checkboxes = []
        try:
            adapters = state.network_manager.get_adapters()
            for adapter in adapters:
                cb = ui.checkbox(f'{adapter.name} (ID: {adapter.id})')
                adapter_checkboxes.append((cb, adapter.id))
        except Exception as e:
            logger.error(f"Failed to get network adapters: {e}")

        with ui.row():
            ui.button('Start Count', on_click=lambda: start_count(state, adapter_checkboxes))
            ui.button('Show Most Recent Gear', on_click=lambda: show_recent_gear(state))

    # Spend section
    with ui.card().classes('w-full'):
        ui.label('Spend Upgrade Attempts').classes('text-h6')

        max_attempts_input = ui.number(
            'Max Attempts',
            value=1,
            min=1,
            max=99,
        ).classes('w-full')

        continue_checkbox = ui.checkbox('Continue upgrade after reaching level 10')

        ui.button('Start Spend', on_click=lambda: start_spend(
            state,
            int(max_attempts_input.value),
            continue_checkbox.value
        ))

async def start_count(state: AppState, adapter_checkboxes: list) -> None:
    """Start count operation in background thread"""
    # Extract selected adapter IDs
    selected_ids = [aid for cb, aid in adapter_checkboxes if cb.value]

    # Run in thread to avoid blocking GUI
    await asyncio.to_thread(_run_count_operation, state, selected_ids)

def _run_count_operation(state: AppState, adapter_ids: list[int]) -> None:
    """Run count operation (calls existing CLI logic)"""
    try:
        window_title = "Raid: Shadow Legends"

        # Validation (same as CLI)
        if not window_exists(window_title):
            logger.warning("Raid window not found. Check if Raid is running.")
            return

        # Network management (same as CLI)
        manager = state.network_manager
        if manager.check_network_access() and not adapter_ids:
            logger.warning(
                "Internet access detected and network id not specified. "
                "This will upgrade the piece. Aborting."
            )
            return

        manager.toggle_adapters(adapter_ids, enable=False)
        # ... rest of count logic from upgrade_cli.py

    except Exception as e:
        logger.error(f"Error during count operation: {e}")

def show_recent_gear(state: AppState) -> None:
    """Show most recent gear via cv2.imshow"""
    try:
        screenshot = state.cache.get("current_gear_counted")
        if screenshot is None:
            logger.warning("No gear piece has been counted yet.")
            return

        cv2.imshow("Most Recent Gear", screenshot)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except Exception as e:
        logger.error(f"Error showing gear: {e}")

async def start_spend(state: AppState, max_attempts: int, continue_upgrade: bool) -> None:
    """Start spend operation in background thread"""
    await asyncio.to_thread(_run_spend_operation, state, max_attempts, continue_upgrade)

def _run_spend_operation(state: AppState, max_attempts: int, continue_upgrade: bool) -> None:
    """Run spend operation (calls existing CLI logic)"""
    # Implementation mirrors upgrade_cli.py spend() command
    # ... reuse existing logic
```

**Key Implementation Strategies:**

1. **Async/Threading**:
   - Use `asyncio.to_thread()` for long-running operations
   - Keeps GUI responsive during count/spend
   - Prevents window freeze

2. **Reuse Existing Logic**:
   - Import functions from `autoupgrade.autoupgrade`
   - Call existing validation and operation functions
   - Pass `state.get_context_dict()` where CLI expects context

3. **Error Handling**:
   - Wrap all operations in try/except
   - Log errors via loguru (appears in GUI log)
   - Use `ui.notify()` for critical errors

---

### 5. components/region_tab.py - Region Management

**Purpose**: Region selection and viewing UI

```python
from nicegui import ui
import asyncio
from loguru import logger

from autoraid.gui.state import AppState
from autoraid.interaction import window_exists, take_screenshot_of_window
from autoraid.autoupgrade.autoupgrade import (
    get_cached_regions,
    get_cached_screenshot,
    select_upgrade_regions,
    create_cache_key_regions,
    create_cache_key_screenshot,
)
from autoraid.visualization import show_regions_in_image
import cv2

def create_region_tab(state: AppState) -> None:
    """Create region management tab"""

    with ui.card().classes('w-full'):
        ui.label('Region Operations').classes('text-h6')

        # Status display
        status_label = ui.label('Click "Refresh Status" to check window')
        ui.button('Refresh Status', on_click=lambda: update_status(status_label, state))

        ui.separator()

        # Show regions
        ui.button('Show Regions', on_click=lambda: show_regions(state))

        ui.separator()

        # Select regions
        manual_checkbox = ui.checkbox('Force manual selection')
        ui.button('Select Regions', on_click=lambda: select_regions(
            state, manual_checkbox.value
        ))

        ui.separator()

        # Save output
        ui.label('Save Regions to Directory:').classes('text-subtitle2')
        output_dir_input = ui.input(
            'Output Directory',
            placeholder='e.g., C:\\Users\\Name\\Desktop\\regions'
        ).classes('w-full')

        ui.button('Show & Save Regions', on_click=lambda: show_and_save(
            state, output_dir_input.value
        ))

def update_status(label: ui.label, state: AppState) -> None:
    """Update region status display"""
    window_title = "Raid: Shadow Legends"

    if not window_exists(window_title):
        label.set_text('❌ Raid window not found')
        return

    screenshot = take_screenshot_of_window(window_title)
    window_size = f"{screenshot.shape[1]}x{screenshot.shape[0]}"

    regions = get_cached_regions(screenshot.shape, state.cache)
    cache_status = "✅ Yes" if regions is not None else "❌ No"

    label.set_text(
        f'Window Size: {window_size} | Regions Cached: {cache_status}'
    )

async def show_regions(state: AppState) -> None:
    """Show cached regions via cv2.imshow"""
    await asyncio.to_thread(_show_regions_impl, state)

def _show_regions_impl(state: AppState) -> None:
    """Implementation of show regions"""
    # Mirrors upgrade_cli.py regions_show() logic
    # ... use get_cached_regions, show_regions_in_image, cv2.imshow

async def select_regions(state: AppState, manual: bool) -> None:
    """Select and cache regions"""
    await asyncio.to_thread(_select_regions_impl, state, manual)

def _select_regions_impl(state: AppState, manual: bool) -> None:
    """Implementation of region selection"""
    # Mirrors upgrade_cli.py regions_select() logic
    # ... use select_upgrade_regions, cache regions

async def show_and_save(state: AppState, output_dir: str) -> None:
    """Show and save regions"""
    await asyncio.to_thread(_show_and_save_impl, state, output_dir)

def _show_and_save_impl(state: AppState, output_dir: str) -> None:
    """Implementation of show and save"""
    # Mirrors upgrade_cli.py regions_show() with --output-dir
    # ... save screenshot, regions JSON, ROIs
```

**Key Features:**
- Status refresh shows window size and cache status
- All cv2.imshow calls remain for image display
- Region selection uses existing `select_upgrade_regions()` function

---

### 6. components/network_tab.py - Network Management

**Purpose**: Network adapter control UI

```python
from nicegui import ui
from loguru import logger

from autoraid.gui.state import AppState
from autoraid.network import NetworkAdapter

def create_network_tab(state: AppState) -> None:
    """Create network adapter management tab"""

    with ui.card().classes('w-full'):
        ui.label('Network Adapters').classes('text-h6')

        # Adapter table
        columns = [
            {'name': 'id', 'label': 'ID', 'field': 'id'},
            {'name': 'name', 'label': 'Name', 'field': 'name'},
            {'name': 'status', 'label': 'Status', 'field': 'status'},
            {'name': 'type', 'label': 'Type', 'field': 'type'},
            {'name': 'speed', 'label': 'Speed', 'field': 'speed'},
        ]

        adapter_table = ui.table(columns=columns, rows=[]).classes('w-full')

        ui.button('Refresh Adapter List', on_click=lambda: refresh_adapters(
            adapter_table, adapter_select, state
        ))

        ui.separator()

        # Adapter selection
        adapter_select = ui.select(
            label='Select Adapter',
            options={},
            value=None
        ).classes('w-full')

        with ui.row():
            ui.button('Enable', on_click=lambda: toggle_adapter(
                state, adapter_select.value, True, adapter_table, adapter_select
            ))
            ui.button('Disable', on_click=lambda: toggle_adapter(
                state, adapter_select.value, False, adapter_table, adapter_select
            ))

        # Initial load
        refresh_adapters(adapter_table, adapter_select, state)

def refresh_adapters(table: ui.table, select: ui.select, state: AppState) -> None:
    """Refresh adapter list"""
    try:
        adapters = state.network_manager.get_adapters()

        # Update table
        rows = []
        options = {}
        for adapter in adapters:
            status = "✅ Enabled" if adapter.enabled else "❌ Disabled"
            speed = (
                f"{adapter.speed / 1000000:.0f} Mbps"
                if adapter.speed is not None
                else "Unknown"
            )

            rows.append({
                'id': adapter.id,
                'name': adapter.name,
                'status': status,
                'type': adapter.adapter_type,
                'speed': speed,
            })

            options[adapter.id] = f"{adapter.id} - {adapter.name}"

        table.rows = rows
        table.update()

        select.options = options
        select.update()

        logger.info(f"Found {len(adapters)} network adapters")

    except Exception as e:
        logger.error(f"Failed to refresh adapters: {e}")

def toggle_adapter(
    state: AppState,
    adapter_id: str,
    enable: bool,
    table: ui.table,
    select: ui.select
) -> None:
    """Enable or disable selected adapter"""
    if adapter_id is None:
        logger.warning("No adapter selected")
        return

    try:
        action = "enable" if enable else "disable"
        success = state.network_manager.toggle_adapter(int(adapter_id), enable)

        if success:
            logger.info(f"Successfully {action}d adapter {adapter_id}")
            ui.notify(f'Adapter {action}d', type='positive')
        else:
            logger.error(f"Failed to {action} adapter {adapter_id}")
            ui.notify(f'Failed to {action} adapter', type='negative')

        # Refresh to show new status
        refresh_adapters(table, select, state)

    except Exception as e:
        logger.error(f"Error toggling adapter: {e}")
        ui.notify(f'Error: {e}', type='negative')
```

**Key Features:**
- Uses NiceGUI table component for adapter display
- Reuses `NetworkManager` from existing code
- Dropdown for adapter selection
- Auto-refresh after enable/disable

---

### 7. utils.py - GUI Utilities

**Purpose**: Helper functions for GUI-specific tasks

```python
from nicegui import ui
from loguru import logger
import sys

def setup_logging(log_display: ui.log) -> None:
    """Setup loguru to output to GUI log display"""

    # Remove default handler
    logger.remove()

    # Add GUI handler
    def gui_sink(message):
        log_display.push(message.rstrip())

    logger.add(
        gui_sink,
        format="{time:HH:mm:ss} | {level: <8} | {message}",
        level="INFO",
    )

    # Also add stderr handler for debugging
    logger.add(
        sys.stderr,
        format="{time:HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
    )

def run_async_operation(coroutine):
    """Helper to run async operation and handle errors"""
    # Placeholder for common async operation wrapper
    pass
```

**Key Features:**
- Custom loguru sink directs logs to GUI
- All logs appear in NiceGUI log component
- Maintains stderr logging for debugging

---

## Threading and Async Strategy

### Problem
Long-running operations (count, spend) will freeze the GUI if run on main thread.

### Solution
Use `asyncio.to_thread()` to run blocking operations in background threads:

```python
async def button_handler():
    # This runs on GUI thread (fast)
    await asyncio.to_thread(long_running_operation)
    # Returns to GUI thread after completion

def long_running_operation():
    # This runs on background thread
    # Can take minutes without freezing GUI
```

### Implementation Pattern

1. **UI Handler** (async function):
   - Validate inputs
   - Call `asyncio.to_thread(implementation_function, args)`
   - Return

2. **Implementation Function** (sync function):
   - Reuse existing CLI logic
   - Call autoupgrade, network, interaction modules
   - Log progress (appears in GUI via loguru)

### Example

```python
# UI layer
async def start_count_button_clicked(state, adapters):
    await asyncio.to_thread(_run_count, state, adapters)

# Implementation layer (reuses CLI logic)
def _run_count(state, adapters):
    # Exact same logic as upgrade_cli.py count() function
    from autoraid.autoupgrade.autoupgrade import count_upgrade_fails
    # ... rest of implementation
```

---

## Logging Integration

### Loguru to NiceGUI Log

**Setup** (in main.py):
```python
log_display = ui.log().classes('w-full h-40')
setup_logging(log_display)
```

**Custom Sink** (in utils.py):
```python
def setup_logging(log_display: ui.log):
    logger.remove()  # Remove default
    logger.add(
        lambda msg: log_display.push(msg.rstrip()),
        format="{time:HH:mm:ss} | {level: <8} | {message}"
    )
```

**Result**:
- All `logger.info()`, `logger.warning()`, `logger.error()` calls appear in GUI
- Existing CLI code needs NO changes
- Background threads can log to GUI

---

## Entry Point Configuration

### Update pyproject.toml

```toml
[project.scripts]
autoraid = "autoraid.cli.cli:autoraid"           # Existing CLI
autoraid-gui = "autoraid.gui.main:main"           # New GUI

[project]
dependencies = [
    # ... existing dependencies ...
    "nicegui>=1.4.0",
]
```

### Usage

After installation:
```bash
# CLI mode (unchanged)
autoraid upgrade count -n 0 -n 1

# GUI mode (new)
autoraid-gui
```

---

## Code Reuse Strategy

### Principle
**Never duplicate business logic**. Always call existing functions.

### Pattern

**Bad** (duplicates logic):
```python
def start_count():
    # Copy-paste from upgrade_cli.py
    screenshot = take_screenshot_of_window(window_title)
    regions = get_regions(screenshot, cache)
    # ... 100 lines of duplicated code
```

**Good** (reuses logic):
```python
def start_count(state, adapter_ids):
    # Import existing function
    from autoraid.cli.upgrade_cli import _run_count_operation

    # Create context compatible with CLI
    ctx_dict = state.get_context_dict()

    # Call existing function
    _run_count_operation(ctx_dict, adapter_ids)
```

### Refactoring Strategy

If CLI functions are too tightly coupled to Click:

1. **Extract Core Logic**:
   - Move business logic from CLI command to separate function
   - Make function accept plain parameters (not Click context)

2. **CLI Wrapper**:
   - CLI command becomes thin wrapper
   - Extracts params from Click context
   - Calls core function

3. **GUI Wrapper**:
   - GUI handler becomes thin wrapper
   - Extracts params from UI controls
   - Calls same core function

**Example**:

```python
# In autoupgrade/operations.py (NEW)
def run_count_operation(
    cache: Cache,
    cache_dir: Path,
    debug_dir: Path | None,
    adapter_ids: list[int],
) -> tuple[int, StopCountReason]:
    """Core count operation logic (CLI-independent)"""
    # ... implementation

# In cli/upgrade_cli.py (MODIFIED)
@upgrade.command()
@click.option("--network-adapter-id", "-n", multiple=True)
def count(network_adapter_id: list[int]):
    ctx = click.get_current_context()
    result = run_count_operation(
        cache=ctx.obj["cache"],
        cache_dir=ctx.obj["cache_dir"],
        debug_dir=ctx.obj["debug_dir"],
        adapter_ids=network_adapter_id,
    )
    logger.info(f"Result: {result}")

# In gui/components/upgrade_tab.py (NEW)
async def start_count(state: AppState, adapter_ids: list[int]):
    result = await asyncio.to_thread(
        run_count_operation,
        cache=state.cache,
        cache_dir=state.cache_dir,
        debug_dir=state.debug_dir,
        adapter_ids=adapter_ids,
    )
    logger.info(f"Result: {result}")
```

---

## Testing Approach

### Manual Testing Checklist

For each GUI control, verify:
1. ✅ Control appears correctly
2. ✅ Control responds to user input
3. ✅ Operation produces same result as CLI
4. ✅ Logs appear in output area
5. ✅ Errors are handled gracefully
6. ✅ GUI remains responsive during operation

### Test Matrix

| Feature | GUI Control | CLI Command | Verification |
|---------|-------------|-------------|--------------|
| Count with network | Checkboxes + button | `upgrade count -n 0` | Same fail count |
| Count without network | Button only | `upgrade count` | Same error message |
| Show gear | Button | `upgrade count -s` | cv2 window opens |
| Spend | Input + button | `upgrade spend -m 5` | Same upgrade result |
| Show regions | Button | `upgrade region show` | cv2 window opens |
| Select regions | Button | `upgrade region select` | Same regions cached |
| List adapters | Table | `network list` | Same adapter list |
| Enable adapter | Dropdown + button | `network enable 0` | Adapter enabled |
| Debug mode | Checkbox | `autoraid --debug` | Debug files saved |

### Automated Testing

**Phase 1**: Manual testing only (GUI testing is complex)

**Phase 2** (future):
- Playwright for GUI automation
- Pytest for unit testing extracted core functions

---

## Deployment and Packaging

### Development

```bash
cd autoraid
uv sync  # Install dependencies including nicegui
uv run autoraid-gui  # Run GUI
```

### Distribution (Future)

Options for distributing GUI application:

1. **PyInstaller**: Package as .exe
2. **Nuitka**: Compile to native executable
3. **pip install**: Install from PyPI

Initial release: Require Python + pip install

---

## Performance Considerations

### GUI Responsiveness
- All operations > 100ms run in background thread
- Use `asyncio.to_thread()` for blocking operations
- NiceGUI event loop handles UI updates

### Memory
- Cache is persistent (disk-based via diskcache)
- Screenshots stored in cache, not in memory
- GUI state is minimal (just control values)

### Startup Time
- NiceGUI native mode has ~2-3 second startup (Chromium launch)
- Acceptable for desktop application

---

## Error Handling Strategy

### Levels

1. **Validation Errors** (UI layer):
   - Check inputs before calling operations
   - Show error notification immediately
   - Don't call backend

2. **Operational Errors** (Business logic):
   - Catch in implementation function
   - Log error
   - Show notification
   - Don't crash GUI

3. **Critical Errors** (Unexpected):
   - Catch at highest level
   - Log full traceback
   - Show error dialog
   - Keep GUI running if possible

### Pattern

```python
async def button_handler(state, inputs):
    # Validation
    if not validate_inputs(inputs):
        ui.notify('Invalid input', type='negative')
        return

    # Operation
    try:
        await asyncio.to_thread(operation, state, inputs)
    except KnownError as e:
        logger.warning(f"Operation failed: {e}")
        ui.notify(f"Operation failed: {e}", type='warning')
    except Exception as e:
        logger.exception("Unexpected error")
        ui.notify(f"Unexpected error: {e}", type='negative')
```

---

## Migration Checklist

### Prerequisites
- [ ] All existing CLI functionality working
- [ ] Existing tests passing
- [ ] Documentation up to date

### Implementation Steps
1. [ ] Add nicegui to pyproject.toml dependencies
2. [ ] Create `src/autoraid/gui/` directory structure
3. [ ] Implement `state.py`
4. [ ] Implement `utils.py` with logging setup
5. [ ] Implement `components/settings.py`
6. [ ] Implement `components/network_tab.py` (simplest)
7. [ ] Implement `components/region_tab.py`
8. [ ] Implement `components/upgrade_tab.py` (most complex)
9. [ ] Implement `main.py`
10. [ ] Add `autoraid-gui` entry point
11. [ ] Test each feature against CLI equivalent
12. [ ] Update README with GUI usage
13. [ ] Create GUI-specific documentation

### Validation
- [ ] All CLI commands have GUI equivalent
- [ ] All operations produce identical results
- [ ] GUI remains responsive during operations
- [ ] Logs display correctly
- [ ] Errors handled gracefully
- [ ] Debug mode works
- [ ] cv2.imshow windows open correctly
- [ ] No new dependencies beyond nicegui

---

## Success Metrics

### Functional Parity
- 100% of CLI functionality available in GUI
- Identical operation results between CLI and GUI
- No regressions in existing CLI

### User Experience
- GUI launches in < 5 seconds
- All operations complete without GUI freeze
- Clear error messages for all failure cases
- Logs provide adequate visibility into operations

### Code Quality
- Zero duplication of business logic
- Clean separation: GUI (presentation) vs. CLI (commands) vs. Core (logic)
- All existing modules unchanged (except potential extraction for reuse)
- Maintainable codebase with clear responsibilities

---

## Future Enhancements (Out of Scope)

These are NOT part of the initial implementation:

- ❌ Embedded image display in GUI
- ❌ Real-time progress bars for operations
- ❌ Settings persistence (save/load preferences)
- ❌ Multi-language support
- ❌ Themes and customization
- ❌ Automated testing framework
- ❌ Packaged executable distribution
- ❌ Auto-update mechanism
- ❌ Telemetry and analytics
- ❌ Advanced network adapter features

Focus: Simple, functional GUI that exactly replicates CLI behavior.
