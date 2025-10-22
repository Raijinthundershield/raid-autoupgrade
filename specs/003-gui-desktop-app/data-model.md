# Data Model: AutoRaid GUI Desktop Application

**Phase**: 1 - Design & Contracts
**Date**: 2025-10-18
**Status**: Complete

## Overview

This document defines the data entities, state management, and persistence strategy for the GUI layer. The GUI introduces minimal new state (UI-specific only) and reuses existing domain entities from the service layer.

**Key Principle**: GUI state is UI-specific only. Domain state lives in existing services (UpgradeStateMachine, CacheService, etc.).

---

## State Architecture

### GUI State (New)

**Storage**: NiceGUI `app.storage.user` (persists across restarts)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `selected_adapters` | `list[int]` | `[]` | Network adapter IDs selected by user for auto-disable during Count workflow |
| `last_count_result` | `int \| None` | `None` | n_fails from last successful Count workflow (for Max Attempts auto-populate) |
| `debug_enabled` | `bool` | `False` | Debug mode toggle state (saves artifacts when True) |

**Lifecycle**: Persists across application restarts, stored in `~/.nicegui/storage/{app_id}/`

---

### Component Local State (Transient)

**Storage**: NiceGUI `ui.state()` (session-only, not persisted)

| Component | State Key | Type | Description |
|-----------|-----------|------|-------------|
| UpgradePanel | `is_count_running` | `bool` | Whether Count workflow is currently executing |
| UpgradePanel | `is_spend_running` | `bool` | Whether Spend workflow is currently executing |
| UpgradePanel | `current_count` | `int` | Real-time count of failures during Count workflow |
| UpgradePanel | `current_spent` | `int` | Real-time count of attempts during Spend workflow |
| UpgradePanel | `workflow_task` | `asyncio.Task \| None` | Reference to running workflow task (for cancellation) |
| UpgradePanel | `max_attempts` | `int` | Max attempts input value for Spend workflow |
| UpgradePanel | `continue_upgrade` | `bool` | Continue upgrade checkbox state (level 10+) |
| RegionPanel | `window_size` | `tuple[int, int] \| None` | Current Raid window size (width, height) |
| RegionPanel | `cached_regions` | `list[str]` | Names of cached regions (upgrade_bar, upgrade_button, artifact_icon) |
| NetworkPanel | `adapters` | `list[dict]` | Current list of network adapters (refreshed on demand) |
| NetworkPanel | `internet_online` | `bool` | Whether internet connection detected |

**Lifecycle**: Reset on application restart, not persisted

---

## Domain Entities (Existing, No Changes)

These entities exist in the service/core layer and are accessed via DI. GUI does not duplicate or modify these.

### Network Adapter (from `platform.network.NetworkManager`)

**Attributes**:
- `id`: int - Adapter ID from Windows WMI
- `name`: str - Human-readable adapter name (e.g., "Ethernet - Intel I211")
- `status`: str - "enabled" or "disabled"

**Operations**:
- `list_all() -> list[NetworkAdapter]` - Retrieve all adapters
- `toggle_adapters(adapter_ids: list[int], enable: bool) -> None` - Enable/disable adapters
- `is_internet_available() -> bool` - Check internet connectivity

**GUI Integration**: NetworkPanel calls these methods directly (no DI for NetworkManager)

---

### Cached Region (from `services.cache_service.CacheService`)

**Attributes**:
- `name`: str - Region name (upgrade_bar, upgrade_button, artifact_icon)
- `left`: int - X coordinate relative to Raid window
- `top`: int - Y coordinate relative to Raid window
- `width`: int - Region width in pixels
- `height`: int - Region height in pixels

**Persistence**: Stored in diskcache, keyed by window size

**Operations**:
- `get_region(window_size: tuple[int, int], name: str) -> Region | None`
- `set_region(window_size: tuple[int, int], name: str, region: Region) -> None`

**GUI Integration**: RegionPanel uses LocateRegionService which wraps CacheService

---

### Workflow State (from `services.upgrade_orchestrator.UpgradeOrchestrator`)

**Count Workflow Result**:
- `n_fails`: int - Number of upgrade failures counted
- `stop_reason`: str - Why workflow stopped ("max_attempts" | "upgraded" | "connection_error")

**Spend Workflow Result**:
- `n_upgrades`: int - Number of successful upgrades
- `n_attempts`: int - Total attempts made
- `n_remaining`: int - Remaining attempts (max_attempts - n_attempts)

**GUI Integration**: UpgradePanel receives these results from orchestrator methods

---

### Debug Artifact (from `services.upgrade_orchestrator.UpgradeOrchestrator`)

**Attributes** (saved to disk when debug mode enabled):
- `screenshots/`: Directory of full window screenshots
- `progress_bar_rois/`: Directory of progress bar region images
- `metadata.json`: Workflow metadata (timestamps, states, n_fails)

**Storage Location**: `cache-raid-autoupgrade/debug/{timestamp}/`

**GUI Integration**: Debug mode checkbox sets `debug_dir` parameter on orchestrator methods

---

### Log Entry (from `loguru` logger)

**Attributes**:
- `level`: str - "INFO" | "DEBUG" | "WARNING" | "ERROR"
- `message`: str - Log message text
- `timestamp`: datetime - When log was emitted

**GUI Integration**: Captured via loguru sink, pushed to `ui.log()` element with color coding

---

## State Transitions

### Network Adapter Selection Flow

```
1. User checks checkbox in NetworkPanel
   → on_adapter_select(adapter_id, selected=True)

2. Update app.storage.user['selected_adapters']
   → append adapter_id to list

3. Display updated selection in Count section
   → Read app.storage.user['selected_adapters'] in UpgradePanel

4. User clicks "Start Count"
   → Pass selected_adapters to orchestrator.count_workflow()
```

**State Storage**: `app.storage.user['selected_adapters']` persists across restarts

---

### Count Workflow Execution Flow

```
1. User clicks "Start Count"
   → is_count_running = True
   → Disable "Start Count" button

2. Orchestrator starts Count workflow in thread
   → asyncio.to_thread(orchestrator.count_workflow, ...)

3. During workflow: State machine emits progress
   → current_count increments on each fail state
   → UI refreshed via ui.refreshable()

4. Workflow completes
   → n_fails returned
   → Store in app.storage.user['last_count_result']
   → Auto-populate Max Attempts input
   → is_count_running = False
   → Re-enable "Start Count" button
```

**State Storage**:
- Transient: `is_count_running`, `current_count` (session-only)
- Persistent: `last_count_result` (survives restart)

---

### Debug Mode Toggle Flow

```
1. User checks "Debug" checkbox in header
   → debug_enabled = True
   → Store in app.storage.user['debug_enabled']

2. User starts Count or Spend workflow
   → Read app.storage.user['debug_enabled']
   → If True: set debug_dir = Path('cache-raid-autoupgrade/debug')
   → Pass debug_dir to orchestrator method

3. Orchestrator saves debug artifacts
   → Screenshots, ROIs, metadata saved to debug_dir/{timestamp}/

4. Logs show artifact save locations
   → "Saved debug screenshot: cache-raid-autoupgrade/debug/..."
```

**State Storage**: `app.storage.user['debug_enabled']` persists across restarts

---

## Data Flow Diagrams

### Count → Spend Auto-Populate

```
┌──────────────────┐
│  UpgradePanel    │
│  (Count Section) │
└────────┬─────────┘
         │ User clicks "Start Count"
         ↓
┌──────────────────────────┐
│  orchestrator.count()    │
│  Returns: n_fails=7      │
└────────┬─────────────────┘
         │ Store result
         ↓
┌──────────────────────────────┐
│  app.storage.user            │
│  ['last_count_result'] = 7   │
└────────┬─────────────────────┘
         │ Read on component init
         ↓
┌──────────────────────────────┐
│  UpgradePanel                │
│  (Spend Section)             │
│  max_attempts_input.value=7  │
└──────────────────────────────┘
```

---

### Network Adapter Selection → Count Workflow

```
┌──────────────────┐
│  NetworkPanel    │
│  User checks box │
└────────┬─────────┘
         │ adapter_id=1, selected=True
         ↓
┌─────────────────────────────┐
│  app.storage.user           │
│  ['selected_adapters']=[1]  │
└────────┬────────────────────┘
         │ Read on Count start
         ↓
┌──────────────────────────────┐
│  UpgradePanel.start_count()  │
│  network_adapter_id=[1]      │
└────────┬─────────────────────┘
         │ Pass to orchestrator
         ↓
┌──────────────────────────────────┐
│  orchestrator.count_workflow()   │
│  Disables adapters [1]           │
└──────────────────────────────────┘
```

---

## Validation Rules

### Network Adapter Selection

- **Rule**: At least 1 adapter must be selected for Count workflow
- **Enforcement**: Show error toast if `selected_adapters` is empty when "Start Count" clicked
- **Error Message**: "No network adapters selected. Please select adapters in Network Adapters section."

### Max Attempts (Spend Workflow)

- **Rule**: Must be integer >= 1
- **Enforcement**: NiceGUI `ui.number()` input with `min=1, step=1`
- **Default**: Auto-populated from `last_count_result` or 1 if no prior count

### Continue Upgrade Checkbox

- **Rule**: Only effective for level 10+ gear
- **Enforcement**: No UI validation (checked via OCR during workflow)
- **Behavior**: Checkbox can be enabled anytime, but orchestrator checks artifact level >= 10

### Debug Mode

- **Rule**: Boolean toggle, no validation
- **Enforcement**: N/A (always valid)
- **Default**: False (disabled)

---

## Persistence Strategy

### What Persists (app.storage.user)

✅ `selected_adapters`: User selections survive restart
✅ `last_count_result`: Max attempts pre-filled after restart
✅ `debug_enabled`: Debug mode state remembered

**Rationale**: These represent user preferences/settings that should persist across sessions

### What Does NOT Persist

❌ `current_count` / `current_spent`: Workflow progress is transient
❌ `is_count_running` / `is_spend_running`: Workflows don't survive restarts
❌ `workflow_task`: Task reference lost on app close
❌ Cached regions: Already persisted in diskcache (separate system)

**Rationale**: Workflows are one-shot operations that don't span sessions. Progress is meaningless after restart.

---

## Caching Strategy (Existing, No Changes)

### Region Cache (diskcache)

**Cache Key**: `f"region_{window_width}x{window_height}_{region_name}"`

**Example**: `region_1920x1080_upgrade_bar`

**Invalidation**: Automatic when window size changes (detected in RegionPanel)

**Storage**: `~/.cache-raid-autoupgrade/` (or custom cache_dir)

**GUI Integration**: RegionPanel shows warning banner if window size changes, prompting re-selection

---

## Entity Relationships

```
┌───────────────────────┐
│  app.storage.user     │
│  (Persistent State)   │
└──────────┬────────────┘
           │ stores
           ↓
┌───────────────────────┐         ┌─────────────────────┐
│  GUI Component State  │ ←─uses─ │  Domain Entities    │
│  (Transient)          │         │  (via Services)     │
└──────────┬────────────┘         └──────────┬──────────┘
           │                                  │
           │ updates                          │ queries
           ↓                                  ↓
┌───────────────────────┐         ┌─────────────────────┐
│  NiceGUI UI Elements  │         │  DI Container       │
│  (Visual Rendering)   │         │  (Service Access)   │
└───────────────────────┘         └─────────────────────┘
```

**Separation of Concerns**:
- **Persistent State**: User preferences in app.storage.user
- **Transient State**: Workflow progress in ui.state()
- **Domain State**: Regions, workflows in services (accessed via DI)
- **UI Rendering**: NiceGUI components (visual only)

---

## Data Access Patterns

### Read-Only Access (Display)

**Use Case**: Show current window size, cached regions status

**Pattern**:
```python
window_size = screenshot_service.get_window_size()  # Via DI
cached_regions = cache_service.list_regions(window_size)  # Via DI
```

**GUI Layer**: RegionPanel displays data, does not modify

---

### Read-Write Access (Mutation)

**Use Case**: Select network adapters, toggle adapters

**Pattern**:
```python
# Read
adapters = network_manager.list_all()  # Direct instantiation

# Write
network_manager.toggle_adapters([1, 2], enable=False)  # Direct call
```

**GUI Layer**: NetworkPanel mutates NetworkManager state

---

### Workflow Execution (Delegation)

**Use Case**: Run Count or Spend workflow

**Pattern**:
```python
result = await asyncio.to_thread(
    orchestrator.count_workflow,
    network_adapter_id=selected_adapters,
    max_attempts=99,
    debug_dir=debug_dir if debug_enabled else None
)
```

**GUI Layer**: UpgradePanel delegates to orchestrator, receives result, updates UI

---

## Summary

- **Minimal New State**: Only UI-specific state added (selections, transient progress)
- **Reuse Domain Entities**: No duplication of Network Adapter, Cached Region, Workflow State
- **Clear Persistence**: User preferences persist, workflow progress does not
- **Separation of Concerns**: GUI state separate from domain state
- **Simple Access Patterns**: DI for services, direct calls for NetworkManager, app.storage for persistence

All data model decisions align with Constitution Principle I (Simplicity) and avoid unnecessary complexity.
