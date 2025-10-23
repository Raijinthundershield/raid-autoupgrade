# Service Contract: NetworkManager

**Version**: 2.0 (Redesign)
**Date**: 2025-10-22
**Feature**: NetworkManager Service Redesign

## Overview

NetworkManager is a Windows-only service providing network adapter management and internet connectivity verification. This contract defines the public API after the redesign to encapsulate network state waiting logic.

**Service Lifecycle**: Singleton (managed by dependency injection container)
**Platform**: Windows only (WMI-based adapter control)
**Dependencies**: Windows WMI, socket (DNS checks), urllib (HTTP checks)

---

## Constants

```python
class NetworkManager:
    """Windows network adapter management service."""

    DEFAULT_DISABLE_TIMEOUT: float = 5.0   # seconds to wait for offline state
    DEFAULT_ENABLE_TIMEOUT: float = 10.0   # seconds to wait for online state
    CHECK_INTERVAL: float = 0.5            # seconds between connectivity checks
```

---

## Public API

### Core Methods (Unchanged)

#### `check_network_access(timeout: float = 5.0) -> bool`

**Purpose**: Check if system has internet connectivity

**Parameters**:
- `timeout` (float, optional): Connection timeout in seconds. Default: 5.0

**Returns**: `bool`
- `True`: Internet connectivity available
- `False`: No internet connectivity

**Behavior**:
- Primary check: DNS query to 8.8.8.8:53 (Google DNS)
- Fallback: HTTP request if DNS fails
- Non-blocking (uses timeout)

**Errors**: No exceptions raised (returns False on failure)

**Example**:
```python
is_online = network_manager.check_network_access()
if is_online:
    print("Network is online")
```

---

#### `get_adapters() -> list[NetworkAdapter]`

**Purpose**: Retrieve all physical network adapters

**Parameters**: None

**Returns**: `list[NetworkAdapter]`
- List of NetworkAdapter objects with attributes: `device_id`, `name`, `enabled`, `adapter_type`
- Empty list if no adapters found

**Behavior**:
- Queries Windows WMI for physical network adapters
- Excludes virtual/loopback adapters

**Errors**: No exceptions raised (returns empty list on WMI failure)

**Example**:
```python
adapters = network_manager.get_adapters()
for adapter in adapters:
    print(f"{adapter.name}: {adapter.enabled}")
```

---

#### `toggle_adapter(adapter_id: str, enable: bool) -> bool`

**Purpose**: Toggle a single network adapter on/off

**Parameters**:
- `adapter_id` (str, required): WMI device ID of adapter
- `enable` (bool, required): True to enable, False to disable

**Returns**: `bool`
- `True`: Toggle operation succeeded
- `False`: Toggle operation failed (invalid ID or WMI error)

**Behavior**:
- Synchronous WMI call to enable/disable adapter
- Returns immediately (does not wait for state change)

**Errors**: No exceptions raised (returns False on failure)

**Example**:
```python
success = network_manager.toggle_adapter("{GUID-12345}", enable=False)
if success:
    print("Adapter disabled")
```

---

### New Methods (Redesign)

#### `wait_for_network_state(expected_online: bool, timeout: float) -> None`

**Purpose**: Block until network reaches expected state or timeout

**Parameters**:
- `expected_online` (bool, required): True for online state, False for offline state
- `timeout` (float, required): Maximum seconds to wait

**Returns**: `None` (succeeds silently)

**Behavior**:
- Polls network state every `CHECK_INTERVAL` (0.5s)
- Requires 2 consecutive checks with expected state before returning (stability guarantee)
- Logs progress every 2 seconds
- Resets consecutive counter if state oscillates

**Errors**:
- **NetworkAdapterError**: Raised if timeout exceeded before reaching expected state
  - Message format: `"Timeout waiting for network to be {online|offline} after {timeout}s"`

**Example**:
```python
try:
    network_manager.wait_for_network_state(expected_online=False, timeout=5.0)
    print("Network confirmed offline")
except NetworkAdapterError as e:
    print(f"Timeout: {e}")
```

---

#### `toggle_adapters(adapter_ids: list[str], enable: bool, wait: bool = False, timeout: float | None = None) -> bool`

**Purpose**: Toggle multiple network adapters with optional state waiting

**Parameters**:
- `adapter_ids` (list[str], required): List of WMI device IDs to toggle
- `enable` (bool, required): True to enable adapters, False to disable
- `wait` (bool, optional): If True, block until network state changes. Default: False
- `timeout` (float | None, optional): Custom timeout in seconds. None uses defaults:
  - 5s for disable operations (`DEFAULT_DISABLE_TIMEOUT`)
  - 10s for enable operations (`DEFAULT_ENABLE_TIMEOUT`)

**Returns**: `bool`
- `True`: At least one adapter toggled successfully
- `False`: All adapter IDs were invalid or toggle operations failed

**Behavior**:
1. **Validation**: Filter out invalid adapter IDs
   - Log warning for each invalid ID: `"Invalid adapter ID: {id}"`
   - Continue with valid IDs only (graceful degradation)
2. **Toggling**: Call `toggle_adapter(id, enable)` for each valid ID sequentially
   - Count successful toggles
   - If count == 0: return False
3. **Waiting** (if `wait=True`):
   - Determine timeout: custom or default based on `enable` flag
   - Call `wait_for_network_state(expected_online=enable, timeout=timeout)`
   - If internet remains after disable: log warning `"Internet still accessible via other network paths"`
4. **Special Case**: If `adapter_ids` is empty: return True (no-op per clarification Q5)

**Errors**:
- **NetworkAdapterError**: Raised if `wait=True` and timeout exceeded
  - Message includes operation type (enable/disable) and timeout value

**Examples**:

*Example 1: Non-blocking disable*
```python
success = network_manager.toggle_adapters(
    adapter_ids=["{GUID-1}", "{GUID-2}"],
    enable=False,
    wait=False
)
if success:
    print("Adapters disabled (not waiting for offline state)")
```

*Example 2: Blocking disable with default timeout*
```python
try:
    network_manager.toggle_adapters(
        adapter_ids=["{GUID-1}"],
        enable=False,
        wait=True  # Uses DEFAULT_DISABLE_TIMEOUT = 5.0s
    )
    print("Network confirmed offline")
except NetworkAdapterError as e:
    print(f"Failed to disable: {e}")
```

*Example 3: Blocking enable with custom timeout*
```python
try:
    network_manager.toggle_adapters(
        adapter_ids=["{GUID-1}", "{GUID-2}"],
        enable=True,
        wait=True,
        timeout=15.0  # Custom 15s timeout
    )
    print("Network confirmed online")
except NetworkAdapterError as e:
    print(f"Failed to enable: {e}")
```

*Example 4: Graceful degradation with invalid IDs*
```python
# Logs warnings for invalid IDs, continues with valid ones
success = network_manager.toggle_adapters(
    adapter_ids=["invalid-id", "{GUID-1}"],  # Mix of invalid + valid
    enable=False,
    wait=True
)
# Output (logs):
# WARNING: Invalid adapter ID: invalid-id
# INFO: Toggled adapter {GUID-1}
```

---

## Removed Methods (Breaking Changes)

These methods have been **removed** from NetworkManager service and moved to CLI layer:

- `display_adapters()` → Moved to `cli/network_cli.py` (uses Rich tables)
- `find_adapter(name: str)` → Moved to `cli/network_cli.py` (search logic)
- `select_adapters()` → Moved to `cli/network_cli.py` (interactive prompts)
- `toggle_selected_adapters()` → Moved to `cli/network_cli.py` (interactive flow)

**Rationale**: NetworkManager is a service layer component, not a UI component. Display and interaction logic belong in CLI layer.

**Migration Path**: CLI commands now inject NetworkManager and handle display/interaction directly using Rich library.

---

## Error Handling

### NetworkAdapterError

**When Raised**:
- Timeout waiting for network state change (in `wait_for_network_state()` and `toggle_adapters()` with `wait=True`)

**Message Format**:
- `"Timeout waiting for network to be {online|offline} after {timeout}s"`

**Example**:
```python
try:
    network_manager.toggle_adapters(ids, enable=False, wait=True, timeout=5.0)
except NetworkAdapterError as e:
    # e.args[0] == "Timeout waiting for network to be offline after 5.0s"
    logger.error(f"Network timeout: {e}")
```

### Warning Conditions (Logged, Not Raised)

| Condition | Log Level | Message Format |
|-----------|-----------|----------------|
| Invalid adapter ID | WARNING | `"Invalid adapter ID: {adapter_id}"` |
| Internet remains after disable | WARNING | `"Internet still accessible via other network paths"` |
| No adapters available | INFO | `"No adapters to toggle (empty list)"` |

---

## Dependency Injection Registration

**Container Registration**:
```python
# src/autoraid/container.py
from dependency_injector import containers, providers
from autoraid.platform.network import NetworkManager

class Container(containers.DeclarativeContainer):
    # ... other providers ...

    network_manager = providers.Singleton(NetworkManager)
```

**CLI Usage**:
```python
# src/autoraid/cli/network_cli.py
from dependency_injector.wiring import inject, Provide
from autoraid.container import Container
from autoraid.platform.network import NetworkManager

@inject
def list_adapters(
    network_manager: NetworkManager = Provide[Container.network_manager],
):
    adapters = network_manager.get_adapters()
    # Display with Rich table (CLI layer)
```

**GUI Usage**:
```python
# src/autoraid/gui/components/network_panel.py
from dependency_injector.wiring import inject, Provide
from autoraid.container import Container
from autoraid.platform.network import NetworkManager

@inject
def create_network_panel(
    network_manager: NetworkManager = Provide[Container.network_manager],
) -> None:
    # Use injected manager instead of NetworkManager()
```

---

## Behavioral Contracts

### Stability Guarantee

**Requirement**: State changes must be stable for 2 consecutive checks before confirming

**Implementation**: `wait_for_network_state()` maintains consecutive check counter:
- Counter resets to 0 when state doesn't match expected
- Counter increments when state matches expected
- Completes when counter reaches 2

**Implication**: Minimum additional latency of 0.5s (1 extra check) when state is stable

---

### Timeout Contracts

| Operation | Default Timeout | Override | When Starts | When Ends |
|-----------|-----------------|----------|-------------|-----------|
| Disable + wait | 5.0s | Via `timeout` param | After last adapter toggled | When offline confirmed or timeout |
| Enable + wait | 10.0s | Via `timeout` param | After last adapter toggled | When online confirmed or timeout |
| No wait | N/A | N/A | Immediately after toggle | Immediately (no waiting) |

**Check Interval**: 0.5s between connectivity checks (constant, not configurable)

---

### Graceful Degradation Contracts

| Scenario | Behavior | Return Value | Errors/Warnings |
|----------|----------|--------------|-----------------|
| All IDs invalid | Skip toggling | `False` | Warnings logged for each invalid ID |
| Some IDs invalid | Toggle valid only | `True` (if ≥1 valid) | Warnings logged for invalid IDs |
| Empty adapter list | No-op | `True` | Info log |
| No adapters available (system-wide) | No-op | `True` | None (silent success) |
| Internet remains after disable | Continue normally | `True` | Warning log |

---

## Backward Compatibility

### API Compatibility

**Unchanged Methods** (100% compatible):
- `check_network_access(timeout: float = 5.0) -> bool`
- `get_adapters() -> list[NetworkAdapter]`
- `toggle_adapter(adapter_id: str, enable: bool) -> bool`

**New Methods** (additive, non-breaking):
- `wait_for_network_state(expected_online: bool, timeout: float) -> None`
- `toggle_adapters(adapter_ids: list[str], enable: bool, wait: bool = False, timeout: float | None = None) -> bool`

**Removed Methods** (breaking, but not used by public API consumers):
- Display/interaction methods moved to CLI layer
- Only internal CLI commands affected (updated in this feature)

### Behavior Compatibility

- Existing workflows continue to work without modification
- New `wait=True` pattern is opt-in (default `wait=False` preserves old behavior)
- Timeout defaults chosen to match typical network adapter behavior

---

## Testing Contract

**Smoke Tests Required** (per pragmatic testing principle):

1. `test_toggle_adapters_without_wait`: Verify immediate return when `wait=False`
2. `test_toggle_adapters_with_wait_success`: Verify `wait_for_network_state` called when `wait=True`
3. `test_toggle_adapters_uses_default_timeout_disable`: Verify 5s timeout for disable
4. `test_toggle_adapters_uses_default_timeout_enable`: Verify 10s timeout for enable
5. `test_wait_for_network_state_immediate_success`: Verify return when state matches (after 2 checks)
6. `test_wait_for_network_state_timeout`: Verify NetworkAdapterError raised on timeout

**Mocking Strategy**: Use `unittest.mock.patch.object` to mock:
- `toggle_adapter()` → return `True` (successful toggle)
- `check_network_access()` → return `True`/`False` (simulate state)
- `time.sleep()` → skip delays in tests

---

## Summary

**Service Type**: Singleton service for Windows network adapter management
**Primary Changes**: Encapsulated waiting logic in `toggle_adapters()` with `wait` parameter
**Breaking Changes**: Removed display/interaction methods (moved to CLI layer)
**Backward Compatibility**: Core API unchanged, new methods are additive
**Error Strategy**: Graceful degradation (warnings) for invalid inputs, errors for timeouts
**Testing**: 6 targeted smoke tests with mocked dependencies

This contract defines the public API for NetworkManager v2.0 after service refactoring. All behavioral guarantees (stability checks, timeout handling, error conditions) are documented for implementation and testing purposes.
