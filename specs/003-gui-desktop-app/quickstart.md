# Quick Start: AutoRaid GUI Development

**Audience**: Developers implementing the GUI feature
**Prerequisites**: AutoRaid development environment set up (see main README.md)
**Status**: Phase 1 complete - Design artifacts ready for implementation

---

## Overview

This guide provides the essential information needed to start implementing the AutoRaid GUI desktop application. All design decisions are documented in detail in the artifacts below - this quickstart extracts only the key points needed to begin coding.

---

## Architecture at a Glance

```
GUI (NiceGUI Native) → DI Container → Existing Services → Core Logic
     ↓ Components
  ├─ UpgradePanel (Count + Spend + Logs)
  ├─ RegionPanel (OpenCV integration)
  └─ NetworkPanel (Adapter management)
```

**Key Principle**: GUI is a **thin presentation layer** - zero business logic duplication

---

## Project Structure

```
src/autoraid/gui/              # NEW MODULE
├── __init__.py
├── app.py                     # Main application entry point
├── components/
│   ├── __init__.py
│   ├── upgrade_panel.py       # Count + Spend workflows
│   ├── region_panel.py        # Region management
│   └── network_panel.py       # Network adapter table
└── utils.py                   # Async helpers, log capture

test/unit/gui/                 # NEW TESTS
├── test_upgrade_panel.py
├── test_region_panel.py
└── test_network_panel.py
```

---

## Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| GUI Framework | NiceGUI | >=2.10.0 | Native desktop window + reactive UI |
| DI | dependency-injector | (existing) | Service injection |
| State | NiceGUI app.storage | (built-in) | Persistent user preferences |
| Async | asyncio | (stdlib) | Non-blocking workflows |
| Logging | loguru | (existing) | Log streaming to UI |

---

## Installation

### Add NiceGUI Dependency

**File**: `pyproject.toml`

```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "nicegui[native]>=2.10.0",
]
```

**Install**:
```bash
cd autoraid
uv sync
```

**Verify**:
```python
python -c "import nicegui; print(nicegui.__version__)"
# Should print 2.10.0 or higher
```

---

## Core Patterns

### 1. Component Structure (Function-Based)

```python
# src/autoraid/gui/components/example_panel.py

from dependency_injector.wiring import inject, Provide
from nicegui import ui
from autoraid.container import Container
from autoraid.services.some_service import SomeService

@inject
def create_example_panel(
    some_service: SomeService = Provide[Container.some_service]
) -> None:
    """Create example UI panel"""

    # Component-local state
    is_running = ui.state({'value': False})

    # Event handlers (defined before UI elements)
    async def on_button_click():
        is_running['value'] = True
        try:
            result = await asyncio.to_thread(some_service.do_work)
            ui.notify(f'Success: {result}', type='positive')
        finally:
            is_running['value'] = False

    # UI elements
    ui.label('Example Panel').classes('text-xl font-bold')
    ui.button('Start').bind_enabled_from(
        is_running, 'value',
        backward=lambda x: not x
    ).on('click', on_button_click)
```

**Key Points**:
- Components are functions, not classes (Principle I: Simplicity)
- Use `@inject` decorator for DI
- Define event handlers before UI elements
- Use `ui.state()` for component-local state

---

### 2. Dependency Injection Setup

**File**: `src/autoraid/gui/app.py`

```python
from autoraid.container import Container
from nicegui import ui

def main():
    """Launch NiceGUI native desktop application"""

    # Create and configure DI container
    container = Container()
    container.config.cache_dir.from_value(Path.home() / '.cache-raid-autoupgrade')
    container.config.debug.from_value(False)

    # Wire GUI modules for @inject decorator
    container.wire(modules=[
        'autoraid.gui.components.upgrade_panel',
        'autoraid.gui.components.region_panel',
    ])

    # Create main UI
    @ui.page('/')
    def index():
        create_header()
        create_upgrade_panel()  # Injected via @inject decorator
        ui.separator()
        create_region_panel()   # Injected via @inject decorator
        ui.separator()
        create_network_panel()  # No injection needed

    # Launch native desktop window
    ui.run(
        native=True,
        window_size=(1200, 800),
        title='AutoRaid',
        reload=False
    )

if __name__ == '__main__':
    main()
```

---

### 3. Async Workflow Pattern

```python
async def start_workflow():
    """Run blocking workflow in thread to keep UI responsive"""

    # Get state from persistent storage
    selected_adapters = app.storage.user.get('selected_adapters', [])
    debug_enabled = app.storage.user.get('debug_enabled', False)

    # Prepare parameters
    debug_dir = Path('cache-raid-autoupgrade/debug') if debug_enabled else None

    # Run blocking call in thread
    try:
        result = await asyncio.to_thread(
            orchestrator.count_workflow,
            network_adapter_id=selected_adapters,
            max_attempts=99,
            debug_dir=debug_dir
        )

        # Store result
        app.storage.user['last_count_result'] = result[0]

        # Show completion
        ui.notify(f'Workflow complete: {result}', type='positive')

    except WindowNotFoundException as e:
        ui.notify(str(e), type='negative')

    finally:
        # Always re-enable UI
        is_running['value'] = False
```

**Key Points**:
- Use `asyncio.to_thread()` for blocking orchestrator calls
- Read persistent state from `app.storage.user`
- Catch specific exceptions, show toast notifications
- Always re-enable UI in `finally` block

---

### 4. Real-Time Updates with Refreshable

```python
@ui.refreshable
def show_count(count: int):
    """Display current count (refreshable)"""
    ui.label(f'Current Count: {count}').classes('text-2xl font-bold text-green-500')

# In workflow loop:
current_count += 1
show_count.refresh(current_count)  # Updates UI
```

**Key Points**:
- Wrap UI section in `@ui.refreshable` decorator
- Call `.refresh(new_value)` to update display
- Works across threads (thread-safe)

---

### 5. Log Streaming

```python
# Set up log capture once (in app.py)
log_output = ui.log(max_lines=1000)

logger.add(
    lambda msg: log_output.push(msg),
    format="{time:HH:mm:ss} | {level:<8} | {message}",
    colorize=True
)

# Logs automatically stream from services
logger.info("This appears in GUI log area")  # Green
logger.error("This appears in red")           # Red
```

---

### 6. Persistent State

```python
# Write (persists across restarts)
app.storage.user['selected_adapters'] = [1, 2]
app.storage.user['last_count_result'] = 7
app.storage.user['debug_enabled'] = True

# Read (with defaults)
selected_adapters = app.storage.user.get('selected_adapters', [])
last_result = app.storage.user.get('last_count_result', None)
debug_enabled = app.storage.user.get('debug_enabled', False)
```

**Storage Location**: `~/.nicegui/storage/{app_id}/`

---

## CLI Integration

**File**: `src/autoraid/cli/cli.py`

```python
@autoraid.command()
def gui():
    """Launch native desktop GUI for AutoRaid"""
    from autoraid.gui.app import main
    main()
```

**Usage**:
```bash
uv run autoraid gui
```

---

## Development Workflow

### Phase 0: Setup (Completed)
✅ Technology research complete (see [research.md](research.md))

### Phase 1: Design (Current)
✅ Data model documented (see [data-model.md](data-model.md))
✅ Component contracts defined (see [contracts/](contracts/))
✅ Quickstart guide created (this file)

### Phase 2: Implementation (Next)
📋 Tasks will be generated via `/speckit.tasks` command

**Suggested Order** (based on dependency graph):
1. Phase 0: Setup NiceGUI Infrastructure
2. Phase 1: Network Adapter Management UI
3. Phase 2: Region Management UI
4. Phase 3: Upgrade Workflows UI (Count + Spend + Logs)
5. Phase 4: Single-Page Layout + Polish
6. Phase 5: Documentation + Testing

---

## Testing Strategy

### Smoke Tests (Unit Level)

**Purpose**: Verify components instantiate without errors, key methods work

**Example**:
```python
# test/unit/gui/test_upgrade_panel.py

from unittest.mock import Mock
from autoraid.services.upgrade_orchestrator import UpgradeOrchestrator
from autoraid.gui.components.upgrade_panel import create_upgrade_panel

def test_create_upgrade_panel_smoke():
    """Verify panel creation without errors"""
    mock_orchestrator = Mock(spec=UpgradeOrchestrator)
    create_upgrade_panel(orchestrator=mock_orchestrator)
    # No exception = pass

def test_start_count_validates_adapters():
    """Verify toast shown when no adapters selected"""
    app.storage.user['selected_adapters'] = []
    # Call async_start_count, verify toast emitted
```

**Run Tests**:
```bash
uv run pytest test/unit/gui/
```

### Manual Testing (Integration Level)

**Checklist-Based**: Each phase has acceptance criteria in contracts

**Example** (UpgradePanel):
- ✅ Click "Start Count" → verify count increments
- ✅ Click "Stop" → verify workflow cancels
- ✅ Logs appear in Live Logs section with color coding

---

## Common Pitfalls & Solutions

### Pitfall 1: UI Blocks During Workflow

**Problem**: Clicking "Start Count" freezes GUI

**Solution**: Use `asyncio.to_thread()` for blocking calls
```python
# BAD (blocks UI)
result = orchestrator.count_workflow()

# GOOD (non-blocking)
result = await asyncio.to_thread(orchestrator.count_workflow)
```

---

### Pitfall 2: Buttons Not Re-Enabling After Error

**Problem**: Button stays disabled after exception

**Solution**: Always use `finally` block
```python
try:
    result = await asyncio.to_thread(workflow)
except Exception as e:
    ui.notify(str(e), type='negative')
finally:
    is_running['value'] = False  # Always re-enable
```

---

### Pitfall 3: OpenCV Window Blocks GUI

**Problem**: `cv2.imshow()` blocks until window closed

**Solution**: Run in thread
```python
await asyncio.to_thread(lambda: (
    cv2.imshow('Regions', img),
    cv2.waitKey(0),
    cv2.destroyAllWindows()
))
```

---

### Pitfall 4: State Not Persisting Across Restarts

**Problem**: Selected adapters reset on app close

**Solution**: Use `app.storage.user`, not `ui.state()`
```python
# BAD (session-only)
selected_adapters = ui.state({'value': []})

# GOOD (persistent)
app.storage.user['selected_adapters'] = []
```

---

## Debugging Tips

### Enable NiceGUI Dev Mode

```python
ui.run(native=True, reload=True)  # Auto-reload on file changes
```

### Inspect Storage

```python
# Print all persistent state
print(app.storage.user._data)
```

### Log UI Events

```python
ui.button('Click Me').on('click', lambda: logger.debug('Button clicked'))
```

---

## Key Documentation

| Document | Purpose | Location |
|----------|---------|----------|
| Feature Spec | User stories, requirements, success criteria | [spec.md](spec.md) |
| Research | Technology decisions, alternatives considered | [research.md](research.md) |
| Data Model | State management, entities, persistence | [data-model.md](data-model.md) |
| Contracts | Component interfaces, event handlers, acceptance criteria | [contracts/](contracts/) |
| Constitution | Project principles (simplicity, pragmatic testing, etc.) | [../../.specify/memory/constitution.md](../../.specify/memory/constitution.md) |

---

## Next Steps

1. **Read Contracts**: Understand component responsibilities
   - [upgrade_panel.md](contracts/upgrade_panel.md)
   - [region_panel.md](contracts/region_panel.md)
   - [network_panel.md](contracts/network_panel.md)

2. **Generate Tasks**: Run `/speckit.tasks` to create implementation tasks

3. **Start Coding**: Begin with Phase 0 (Setup NiceGUI Infrastructure)

4. **Test Incrementally**: Smoke test each component as you build

5. **Manual Verification**: Use acceptance criteria checklists from contracts

---

## Getting Help

- **NiceGUI Docs**: https://nicegui.io/documentation
- **Existing Services**: See `src/autoraid/services/` for service interfaces
- **Constitution**: Refer to principles when making design decisions
- **Technical Spec**: See `plans/gui-technical.md` for detailed patterns

---

## Constitution Reminders

✅ **Simplicity**: No complex abstractions, straightforward patterns
✅ **Readability**: Clear names, domain concepts, self-documenting code
✅ **Pragmatic Testing**: Smoke tests + manual verification (no GUI automation)
✅ **Debug-Friendly**: Preserve debug mode, real-time logs, clear error messages
✅ **Incremental**: Deliver each phase independently, test before moving on

When in doubt: **Simple > Clever**
