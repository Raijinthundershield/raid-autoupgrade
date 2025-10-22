# Contract: NetworkPanel Component

**Module**: `src/autoraid/gui/components/network_panel.py`
**Responsibility**: Display network adapters table, manage selection, and enable/disable adapters
**UI Location**: Bottom section of single-page scrollable layout

---

## Dependencies (Direct Instantiation)

```python
def create_network_panel() -> None:
    """Create network adapter management UI section"""
    network_manager = NetworkManager()  # Direct instantiation (not via DI)
```

**Service Dependencies**:
- `NetworkManager` (from `platform.network`): Instantiated directly, not injected

**Rationale**: NetworkManager is a simple utility class with no state, no need for DI complexity

**State Dependencies**:
- `app.storage.user['selected_adapters']`: Read/write selected adapter IDs (persists across restarts)

---

## Public Interface

### Function: `create_network_panel() -> None`

**Purpose**: Render network adapters table with multi-select and management buttons

**Returns**: None (mutates NiceGUI UI tree)

**Side Effects**:
- Adds UI elements to current NiceGUI container
- Registers event handlers for checkbox clicks and button clicks
- Sets up timer for internet status polling

---

## UI Elements

### Header: Internet Status Indicator

- **Element**: `ui.row()` with icon + label
- **Format**:
  - **Online**: "🟢 Internet: Online" (green)
  - **Offline**: "🔴 Internet: Offline" (red)
- **Value**: Retrieved via `network_manager.is_internet_available()`
- **Updates**: Every 5 seconds via `ui.timer()`

---

### Table: Network Adapters

**Columns**:
1. **Select** (Checkbox): Multi-select for Count workflow
2. **ID**: Adapter ID (int)
3. **Name**: Human-readable adapter name (str)
4. **Status**: "Enabled" (green) or "Disabled" (red)

**Data Source**: `network_manager.list_all()`

**Rendering**:
- Each row rendered with `ui.row()` containing:
  - `ui.checkbox()` for selection (bound to `app.storage.user['selected_adapters']`)
  - `ui.label()` for ID, Name, Status
- Status displayed with colored text (green for enabled, red for disabled)

**Updates**: On component mount + when "Refresh" button clicked

---

### Checkbox: Select Adapter

- **Element**: `ui.checkbox()` per adapter row
- **State**: Checked if `adapter_id in app.storage.user['selected_adapters']`
- **Change Handler**: `on_adapter_select(adapter_id, checked)`

---

### Button: Refresh

- **Element**: `ui.button('Refresh')`
- **Enabled State**: Always enabled
- **Click Handler**: `refresh_adapters()`
- **Tooltip**: "Reload adapter list with updated status"

---

### Button: Enable / Disable (per adapter row)

**Optional Enhancement** (not MVP):
- **Element**: `ui.button('Enable')` or `ui.button('Disable')` per row
- **Visibility**: "Enable" shown when disabled, "Disable" shown when enabled
- **Click Handler**: `toggle_adapter(adapter_id, enable: bool)`

---

## Event Handlers

### `on_adapter_select(adapter_id: int, checked: bool) -> None`

**Purpose**: Update selected adapters list when checkbox toggled

**Workflow**:
1. Read current selected adapters from `app.storage.user['selected_adapters']` (default=[])
2. If `checked=True`:
   - Add `adapter_id` to list if not already present
3. If `checked=False`:
   - Remove `adapter_id` from list if present
4. Write updated list back to `app.storage.user['selected_adapters']`

**Side Effects**:
- Selected adapters persisted across restarts
- Count workflow reads this list when "Start Count" clicked

**Validation**: None (any number of adapters can be selected, including zero)

---

### `refresh_adapters() -> None`

**Purpose**: Reload adapter table with updated status

**Workflow**:
1. Call `network_manager.list_all()` to get fresh adapter list
2. Refresh table UI via `@ui.refreshable` decorator:
   ```python
   @ui.refreshable
   def show_adapter_table(adapters: list[dict]):
       for adapter in adapters:
           render_adapter_row(adapter)

   show_adapter_table.refresh(new_adapters_list)
   ```
3. Update internet status indicator simultaneously

**Error Handling**:
- If `network_manager.list_all()` raises exception: show toast "Failed to refresh adapters"

**Side Effects**:
- Table re-rendered with latest adapter status
- Internet status indicator updated

---

### `toggle_adapter(adapter_id: int, enable: bool) -> None` *(Optional)*

**Purpose**: Manually enable or disable a specific adapter

**Workflow**:
1. Call `network_manager.toggle_adapters([adapter_id], enable=enable)`
2. Wait for operation to complete
3. Refresh adapter table to show updated status
4. Show toast:
   - **Enable**: "Adapter {adapter_id} enabled"
   - **Disable**: "Adapter {adapter_id} disabled"

**Error Handling**:
- `NetworkAdapterError`: Toast "Failed to toggle adapter {adapter_id}. Check admin rights."

**Side Effects**:
- Adapter status changed in Windows
- Table refreshed to reflect new status

**Admin Rights**: May require admin privileges (same as CLI)

---

## State Management

### Persistent State (app.storage.user)

| Key | Type | Read/Write | Purpose |
|-----|------|------------|---------|
| `selected_adapters` | `list[int]` | Read/Write | Adapter IDs selected for auto-disable during Count workflow |

**Lifecycle**: Persists across application restarts

---

### Transient State (Component-Local)

| Variable | Type | Initial | Purpose |
|----------|------|---------|---------|
| `adapters` | `list[dict]` | `[]` | Current adapter list from `NetworkManager.list_all()` |
| `internet_online` | `bool` | `True` | Whether internet connection detected |

**Lifecycle**: Reset on application restart, refreshed on demand

---

## Internet Status Polling

### Timer: Check Internet Every 5 Seconds

```python
ui.timer(interval=5.0, callback=refresh_internet_status)
```

**Behavior**:
1. Call `network_manager.is_internet_available()`
2. Update internet status indicator:
   - **True**: "🟢 Internet: Online" (green)
   - **False**: "🔴 Internet: Offline" (red)
3. Refresh indicator UI via `@ui.refreshable` decorator

**Purpose**: Provide real-time feedback on network connectivity

---

## Acceptance Criteria

### Adapter Table
- ✅ Table displays all adapters with ID, Name, Status columns
- ✅ Checkboxes allow multi-select (any number of adapters)
- ✅ Selected adapters persist across application restarts
- ✅ Refresh button reloads table with updated status
- ✅ Status displayed with color coding (green=enabled, red=disabled)

### Internet Status
- ✅ Internet status indicator shows correct state (online/offline)
- ✅ Indicator updates every 5 seconds
- ✅ Color coding: green for online, red for offline

### Adapter Selection
- ✅ Checking checkbox adds adapter to `app.storage.user['selected_adapters']`
- ✅ Unchecking checkbox removes adapter from list
- ✅ Selected adapters displayed in Count section (read from storage)
- ✅ Empty selection allowed (no validation error)

### Manual Toggle (Optional)
- ✅ Enable/Disable buttons toggle adapter status
- ✅ Toast notification shows success/failure
- ✅ Table refreshes after toggle to show updated status

---

## Testing Strategy

### Smoke Tests (Unit)

```python
def test_create_network_panel_smoke():
    """Verify panel creation without errors"""
    create_network_panel()
    # Verify no exceptions raised

def test_adapter_select_updates_storage():
    """Verify checkbox updates app.storage.user"""
    app.storage.user['selected_adapters'] = []
    on_adapter_select(adapter_id=1, checked=True)
    assert 1 in app.storage.user['selected_adapters']

def test_adapter_deselect_updates_storage():
    """Verify unchecking removes from storage"""
    app.storage.user['selected_adapters'] = [1, 2]
    on_adapter_select(adapter_id=1, checked=False)
    assert 1 not in app.storage.user['selected_adapters']
    assert 2 in app.storage.user['selected_adapters']

def test_refresh_adapters_calls_list_all():
    """Verify refresh calls NetworkManager.list_all()"""
    mock_network_manager = Mock()
    refresh_adapters()
    mock_network_manager.list_all.assert_called_once()
```

### Manual Tests (Integration)

- Check 2 adapters, restart application → Verify checkboxes remain checked
- Disable network manually (Windows settings), click Refresh → Verify table shows "Offline"
- Select adapters in NetworkPanel, navigate to Count section → Verify adapter names displayed
- Click Refresh button → Verify table reloads with updated status

---

## Implementation Notes

### Refreshable Table Pattern

```python
@ui.refreshable
def show_adapter_table(adapters: list[dict]):
    with ui.column():
        # Header row
        with ui.row().classes('font-bold'):
            ui.label('Select')
            ui.label('ID')
            ui.label('Name')
            ui.label('Status')

        # Data rows
        for adapter in adapters:
            with ui.row():
                ui.checkbox(
                    value=adapter['id'] in app.storage.user.get('selected_adapters', []),
                    on_change=lambda e, aid=adapter['id']: on_adapter_select(aid, e.value)
                )
                ui.label(str(adapter['id']))
                ui.label(adapter['name'])
                ui.label(adapter['status']).classes(
                    'text-green-500' if adapter['status'] == 'enabled' else 'text-red-500'
                )

# Refresh on demand
show_adapter_table.refresh(new_adapters_list)
```

### Internet Status Indicator

```python
@ui.refreshable
def show_internet_status(online: bool):
    icon = '🟢' if online else '🔴'
    color = 'text-green-500' if online else 'text-red-500'
    ui.label(f'{icon} Internet: {"Online" if online else "Offline"}').classes(color)

# Update every 5 seconds
ui.timer(interval=5.0, callback=lambda: show_internet_status.refresh(network_manager.is_internet_available()))
```

### Persistent Selection

```python
def on_adapter_select(adapter_id: int, checked: bool):
    adapters = app.storage.user.get('selected_adapters', [])

    if checked and adapter_id not in adapters:
        adapters.append(adapter_id)
    elif not checked and adapter_id in adapters:
        adapters.remove(adapter_id)

    app.storage.user['selected_adapters'] = adapters
```

---

## Dependencies Summary

**From platform.network**:
- `NetworkManager` (direct instantiation)
  - `list_all() -> list[dict]`
  - `is_internet_available() -> bool`
  - `toggle_adapters(adapter_ids: list[int], enable: bool) -> None`

**From NiceGUI**:
- `app.storage.user` (persistent state)
- `ui.table()`, `ui.checkbox()`, `ui.button()`, `ui.label()`, `ui.row()`
- `ui.notify()` (toast notifications)
- `ui.refreshable()` (reactive updates)
- `ui.timer()` (periodic polling)

**From Python stdlib**:
- None (synchronous operations only)

---

## Notes

### Why Not Use DI for NetworkManager?

**Rationale**:
- NetworkManager is stateless utility class
- No complex lifetime management needed
- No mocking required (smoke tests verify instantiation only)
- Simplicity over consistency (Principle I)

If future needs require DI (e.g., testing with mock WMI), can refactor to:
```python
@inject
def create_network_panel(
    network_manager: NetworkManager = Provide[Container.network_manager]
) -> None:
    ...
```

### Admin Rights Requirement

- Disabling/enabling adapters requires admin privileges
- Same requirement as CLI (`autoraid network disable`)
- User must launch GUI as administrator if using network adapter features
- Error toast provides clear guidance if WMI access fails
