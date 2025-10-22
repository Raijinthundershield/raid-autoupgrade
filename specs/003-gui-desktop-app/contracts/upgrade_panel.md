# Contract: UpgradePanel Component

**Module**: `src/autoraid/gui/components/upgrade_panel.py`
**Responsibility**: Orchestrate Count and Spend upgrade workflows with real-time feedback
**UI Location**: Top section of single-page scrollable layout

---

## Dependencies (Injected via DI)

```python
@inject
def create_upgrade_panel(
    orchestrator: UpgradeOrchestrator = Provide[Container.upgrade_orchestrator]
) -> None:
    """Create upgrade workflows UI section"""
```

**Service Dependencies**:
- `UpgradeOrchestrator`: For executing count_workflow() and spend_workflow()

**State Dependencies**:
- `app.storage.user['selected_adapters']`: Read network adapters selected in NetworkPanel
- `app.storage.user['last_count_result']`: Read/write last count result for Max Attempts auto-populate
- `app.storage.user['debug_enabled']`: Read debug mode toggle state

---

## Public Interface

### Function: `create_upgrade_panel(orchestrator: UpgradeOrchestrator) -> None`

**Purpose**: Render Count + Spend + Live Logs UI section

**Returns**: None (mutates NiceGUI UI tree)

**Side Effects**:
- Adds UI elements to current NiceGUI container
- Registers event handlers for button clicks
- Sets up log capture sink
- Initializes refreshable UI sections

---

## UI Elements

### Count Section (Left)

#### Read-Only Display: Selected Network Adapters
- **Element**: `ui.input()` with readonly=True
- **Value**: Comma-separated adapter names from `app.storage.user['selected_adapters']`
- **Updates**: On component mount (reads from storage)

#### Button: Start Count
- **Element**: `ui.button('Start Count')`
- **Enabled State**: Disabled when `is_count_running` is True
- **Click Handler**: `async_start_count()`

#### Display: Current Count
- **Element**: `ui.label()` inside `@ui.refreshable` decorator
- **Value**: `current_count` (int, starts at 0)
- **Updates**: Real-time during workflow execution

---

### Spend Section (Right)

#### Input: Max Attempts
- **Element**: `ui.number(min=1, step=1)`
- **Default Value**: `app.storage.user['last_count_result']` or 1
- **Validation**: Integer >= 1 (enforced by NiceGUI)

#### Checkbox: Continue Upgrade
- **Element**: `ui.checkbox('Continue Upgrade (Level 10+)')`
- **Default**: Unchecked (False)
- **Behavior**: Passed to orchestrator, checked via OCR during workflow

#### Button: Start Spend
- **Element**: `ui.button('Start Spend')`
- **Enabled State**: Disabled when `is_spend_running` is True
- **Click Handler**: `async_start_spend()`

#### Display: Current Spent
- **Element**: `ui.label()` inside `@ui.refreshable` decorator
- **Value**: `current_spent` (int, starts at 0)
- **Updates**: Real-time during workflow execution

---

### Live Logs Section (Bottom, Shared)

#### Log Display
- **Element**: `ui.log(max_lines=1000)`
- **Color Coding**: INFO=green, DEBUG=blue, WARNING=yellow, ERROR=red
- **Auto-Scroll**: Enabled by default
- **Updates**: Real-time via loguru sink

#### Button: Stop
- **Element**: `ui.button('Stop')`
- **Enabled State**: Enabled only when workflow is running
- **Click Handler**: `async_stop_workflow()`

---

## Event Handlers

### `async_start_count() -> None`

**Preconditions**:
- At least 1 network adapter selected in `app.storage.user['selected_adapters']`
- Raid window exists (checked by orchestrator)
- Cached regions exist for current window size

**Workflow**:
1. Validate preconditions
   - If no adapters selected: show toast "No network adapters selected"
   - If no cached regions: show toast "No cached regions found. Please select regions first." + scroll to RegionPanel
2. Set `is_count_running = True`
3. Clear log area
4. Read selected_adapters from `app.storage.user`
5. Read debug_enabled from `app.storage.user`
6. Create workflow task: `asyncio.create_task(run_count_workflow())`
7. Store task reference in component state

**Error Handling**:
- `WindowNotFoundException`: Toast "Raid window not found. Check if Raid is running."
- `NetworkAdapterError`: Toast "Failed to disable network. Check adapter IDs."
- `CacheKeyError` (no regions): Toast "No cached regions found. Please select regions first."

**Finally Block**:
- Set `is_count_running = False`
- Re-enable "Start Count" button

---

### `run_count_workflow() -> None`

**Async Workflow** (runs in thread):

```python
selected_adapters = app.storage.user.get('selected_adapters', [])
debug_dir = Path('cache-raid-autoupgrade/debug') if app.storage.user.get('debug_enabled') else None

n_fails, stop_reason = await asyncio.to_thread(
    orchestrator.count_workflow,
    network_adapter_id=selected_adapters,
    max_attempts=99,
    debug_dir=debug_dir
)

# Store result
app.storage.user['last_count_result'] = n_fails

# Auto-populate Max Attempts in Spend section
max_attempts_input.value = n_fails

# Show completion toast
ui.notify(f'Count complete: {n_fails} fails ({stop_reason})', type='positive')
```

**Real-Time Updates**:
- `current_count` increments on each fail state detected
- Refresh via `show_count.refresh(current_count)`

---

### `async_start_spend() -> None`

**Preconditions**:
- Max attempts >= 1 (validated by ui.number input)
- Internet access available (checked by orchestrator)
- Cached regions exist

**Workflow**:
1. Validate preconditions
   - If no internet: show toast "No internet access detected. Aborting."
   - If no cached regions: show toast "No cached regions found. Please select regions first."
2. Set `is_spend_running = True`
3. Clear log area
4. Read max_attempts from input
5. Read continue_upgrade from checkbox
6. Read debug_enabled from `app.storage.user`
7. Create workflow task: `asyncio.create_task(run_spend_workflow())`
8. Store task reference

**Error Handling**:
- `WindowNotFoundException`: Toast "Raid window not found. Check if Raid is running."
- `UpgradeWorkflowError`: Toast with exception message

**Finally Block**:
- Set `is_spend_running = False`
- Re-enable "Start Spend" button

---

### `run_spend_workflow() -> None`

**Async Workflow** (runs in thread):

```python
max_attempts = max_attempts_input.value
continue_upgrade = continue_upgrade_checkbox.value
debug_dir = Path('cache-raid-autoupgrade/debug') if app.storage.user.get('debug_enabled') else None

n_upgrades, n_attempts, n_remaining = await asyncio.to_thread(
    orchestrator.spend_workflow,
    max_attempts=max_attempts,
    continue_upgrade=continue_upgrade,
    debug_dir=debug_dir
)

# Show completion toast
ui.notify(f'Spend complete: {n_upgrades} upgrades, {n_attempts} attempts, {n_remaining} remaining', type='positive')
```

**Real-Time Updates**:
- `current_spent` increments on each attempt
- Refresh via `show_spent.refresh(current_spent)`

---

### `async_stop_workflow() -> None`

**Behavior**:
1. Cancel workflow task: `workflow_task.cancel()`
2. Await task to handle CancelledError:
   ```python
   try:
       await workflow_task
   except asyncio.CancelledError:
       ui.notify('Workflow cancelled', type='warning')
   ```
3. Finally block in workflow ensures cleanup (re-enable network adapters)

**Side Effects**:
- Network adapters re-enabled (if disabled)
- Workflow state reset
- Buttons re-enabled

---

## State Management

### Transient State (Component-Local)

| Variable | Type | Initial | Purpose |
|----------|------|---------|---------|
| `is_count_running` | `bool` | `False` | Disable button during Count workflow |
| `is_spend_running` | `bool` | `False` | Disable button during Spend workflow |
| `current_count` | `int` | `0` | Real-time fail count display |
| `current_spent` | `int` | `0` | Real-time attempt count display |
| `workflow_task` | `asyncio.Task \| None` | `None` | Reference to running task (for cancellation) |

### Persistent State (app.storage.user)

| Key | Type | Read/Write | Purpose |
|-----|------|------------|---------|
| `selected_adapters` | `list[int]` | Read | Network adapters to disable during Count |
| `last_count_result` | `int` | Read/Write | n_fails from last Count (for Max Attempts auto-populate) |
| `debug_enabled` | `bool` | Read | Whether to save debug artifacts |

---

## Log Streaming Implementation

### Loguru Sink Setup

```python
log_output = ui.log(max_lines=1000)

logger.add(
    lambda msg: log_output.push(msg),
    format="{time:HH:mm:ss} | {level:<8} | {message}",
    colorize=True
)
```

### Color Mapping

- INFO → Green
- DEBUG → Blue
- WARNING → Yellow
- ERROR → Red

### Auto-Clear Behavior

Log area clears when new workflow starts (before first log emission)

---

## Acceptance Criteria

### Count Workflow
- ✅ "Start Count" disabled when Count running
- ✅ Network adapters disabled before workflow starts
- ✅ Current Count updates in real-time (<500ms latency)
- ✅ Logs stream to Live Logs section with color coding
- ✅ Stop button cancels workflow and re-enables network
- ✅ Toast shows completion: "Count complete: X fails (reason)"
- ✅ Max Attempts auto-populates with n_fails after Count completes

### Spend Workflow
- ✅ "Start Spend" disabled when Spend running
- ✅ Internet access validated before workflow starts
- ✅ Current Spent updates in real-time (<500ms latency)
- ✅ Logs stream to Live Logs section
- ✅ Stop button cancels workflow
- ✅ Toast shows completion: "Spend complete: X upgrades, Y attempts, Z remaining"

### Error Handling
- ✅ Toast shown for WindowNotFoundException
- ✅ Toast shown for NetworkAdapterError
- ✅ Toast shown for no cached regions (with scroll to RegionPanel)
- ✅ Toast shown for no internet access during Spend
- ✅ Toast shown when workflow cancelled via Stop button

### State Persistence
- ✅ last_count_result persists across app restarts
- ✅ Max Attempts pre-filled from last_count_result on startup
- ✅ Current Count/Spent reset to 0 on app restart

---

## Testing Strategy

### Smoke Tests (Unit)

```python
def test_create_upgrade_panel_smoke():
    """Verify panel creation without errors"""
    mock_orchestrator = Mock(spec=UpgradeOrchestrator)
    create_upgrade_panel(orchestrator=mock_orchestrator)
    # Verify no exceptions raised

def test_start_count_validates_adapters():
    """Verify toast shown when no adapters selected"""
    app.storage.user['selected_adapters'] = []
    async_start_count()
    # Verify toast notification emitted

def test_max_attempts_auto_populated():
    """Verify Max Attempts input filled from last_count_result"""
    app.storage.user['last_count_result'] = 7
    create_upgrade_panel(mock_orchestrator)
    assert max_attempts_input.value == 7
```

### Manual Tests (Integration)

- Navigate to GUI, select adapters, click Start Count, verify count increments
- Start Count workflow, click Stop, verify workflow cancels and network re-enables
- Complete Count workflow, navigate to Spend section, verify Max Attempts auto-filled
- Enable debug mode, run Count, verify debug artifacts saved

---

## Implementation Notes

### Refreshable UI Pattern

```python
@ui.refreshable
def show_count(count: int):
    ui.label(f'Current Count: {count}').classes('text-2xl font-bold text-green-500')

# Update display
show_count.refresh(new_count_value)
```

### Button State Binding

```python
is_running = ui.state({'value': False})

ui.button('Start Count').bind_enabled_from(
    is_running, 'value',
    backward=lambda x: not x  # Enabled when NOT running
)
```

### Async Task Cancellation

```python
workflow_task = asyncio.create_task(run_count_workflow())

# Later, in stop handler
workflow_task.cancel()
try:
    await workflow_task
except asyncio.CancelledError:
    pass  # Expected
```

---

## Dependencies Summary

**From DI Container**:
- `UpgradeOrchestrator` (factory provider)

**From NiceGUI**:
- `app.storage.user` (persistent state)
- `ui.state()` (component-local state)
- `ui.log()`, `ui.button()`, `ui.input()`, `ui.number()`, `ui.checkbox()`, `ui.label()`
- `ui.notify()` (toast notifications)
- `ui.refreshable()` (reactive updates)

**From Python stdlib**:
- `asyncio` (async/await, tasks, threading)
- `pathlib.Path` (debug directory)
