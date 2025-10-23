# Quickstart: NetworkManager Service Redesign

**Feature**: NetworkManager Service Redesign
**Date**: 2025-10-22
**For**: Developers implementing or using the redesigned NetworkManager service

## Overview

This quickstart guide shows how to use the redesigned NetworkManager service API with encapsulated waiting logic. The key change is the new `toggle_adapters()` method with automatic network state verification.

---

## What Changed

### Before (Old Pattern)

```python
# Manual waiting loop in every workflow
network_manager.toggle_adapters(adapter_ids, enable=False)

logger.info("Waiting for network to turn off...")
start_time = time.time()
timeout = 5.0

while True:
    time.sleep(0.5)
    if not network_manager.check_network_access():
        logger.info("Network is offline")
        break
    if time.time() - start_time > timeout:
        raise NetworkAdapterError("Timeout waiting for network to go offline")
```

### After (New Pattern)

```python
# Automatic waiting - one line!
network_manager.toggle_adapters(adapter_ids, enable=False, wait=True)
# Network confirmed offline when this returns
```

**Benefits**:
- 10-15 lines → 1 line
- No manual timeout logic
- Consistent error handling
- Stability guarantee (2 consecutive checks)

---

## Quick Examples

### Example 1: Disable adapters with automatic waiting

```python
from autoraid.platform.network import NetworkManager
from autoraid.exceptions import NetworkAdapterError

# Get manager via dependency injection (see "Using in Your Code" section)
network_manager = ...

try:
    # Disable adapters and wait for offline confirmation (5s timeout default)
    network_manager.toggle_adapters(
        adapter_ids=["{GUID-1}", "{GUID-2}"],
        enable=False,
        wait=True
    )
    print("✓ Network is now offline")
except NetworkAdapterError as e:
    print(f"✗ Failed to disable network: {e}")
```

---

### Example 2: Enable adapters with custom timeout

```python
try:
    # Enable adapters and wait for online confirmation (custom 15s timeout)
    network_manager.toggle_adapters(
        adapter_ids=["{GUID-1}"],
        enable=True,
        wait=True,
        timeout=15.0  # Override default 10s timeout
    )
    print("✓ Network is now online")
except NetworkAdapterError as e:
    print(f"✗ Failed to enable network: {e}")
```

---

### Example 3: Non-blocking toggle for cleanup code

```python
try:
    # ... workflow logic ...
    pass
except Exception as e:
    logger.error(f"Workflow failed: {e}")
finally:
    # Re-enable adapters without waiting (cleanup shouldn't block)
    network_manager.toggle_adapters(
        adapter_ids=["{GUID-1}"],
        enable=True,
        wait=False  # Returns immediately
    )
    print("✓ Adapters re-enabled (not waiting for online state)")
```

---

### Example 4: Getting available adapters

```python
# Get all physical network adapters
adapters = network_manager.get_adapters()

print("Available adapters:")
for adapter in adapters:
    status = "Enabled" if adapter.enabled else "Disabled"
    print(f"  - {adapter.name} ({adapter.device_id}): {status}")

# Extract adapter IDs for toggling
adapter_ids = [adapter.device_id for adapter in adapters]
```

---

## Using in Your Code

### Option 1: Dependency Injection (Recommended)

**For CLI commands**:
```python
# src/autoraid/cli/network_cli.py
from dependency_injector.wiring import inject, Provide
from autoraid.container import Container
from autoraid.platform.network import NetworkManager

@inject
def my_command(
    network_manager: NetworkManager = Provide[Container.network_manager],
):
    # Use network_manager here
    adapters = network_manager.get_adapters()
    # ...
```

**For services/orchestrators**:
```python
# src/autoraid/services/upgrade_orchestrator.py
from dependency_injector.wiring import inject, Provide
from autoraid.container import Container
from autoraid.platform.network import NetworkManager

class UpgradeOrchestrator:
    @inject
    def __init__(
        self,
        network_manager: NetworkManager = Provide[Container.network_manager],
        # ... other dependencies ...
    ):
        self.network_manager = network_manager
```

**For GUI components**:
```python
# src/autoraid/gui/components/network_panel.py
from dependency_injector.wiring import inject, Provide
from autoraid.container import Container
from autoraid.platform.network import NetworkManager

@inject
def create_network_panel(
    network_manager: NetworkManager = Provide[Container.network_manager],
) -> None:
    # Use network_manager here
    adapters = network_manager.get_adapters()
    # ...
```

### Option 2: Manual Instantiation (Not Recommended)

```python
# Only for testing or standalone scripts
from autoraid.platform.network import NetworkManager

network_manager = NetworkManager()
# Note: This bypasses dependency injection and is harder to test
```

---

## Common Patterns

### Pattern 1: Workflow with Network Toggle

```python
@inject
def count_workflow(
    network_adapter_id: str | None,
    max_attempts: int,
    network_manager: NetworkManager = Provide[Container.network_manager],
):
    """Upgrade counting workflow with automatic network handling."""

    try:
        # Disable network and wait for offline confirmation
        if network_adapter_id:
            network_manager.toggle_adapters(
                adapter_ids=[network_adapter_id],
                enable=False,
                wait=True  # Uses DEFAULT_DISABLE_TIMEOUT = 5.0s
            )
            logger.info("Network disabled")

        # ... perform upgrade counting logic ...

    finally:
        # Always re-enable network (non-blocking for fast cleanup)
        if network_adapter_id:
            network_manager.toggle_adapters(
                adapter_ids=[network_adapter_id],
                enable=True,
                wait=False  # Returns immediately
            )
            logger.info("Network re-enabled")
```

---

### Pattern 2: Multiple Adapters with Validation

```python
def toggle_multiple_adapters(adapter_names: list[str]):
    """Toggle multiple adapters by name, handling invalid names gracefully."""

    # Get all available adapters
    all_adapters = network_manager.get_adapters()

    # Find adapter IDs matching requested names
    adapter_ids = []
    for name in adapter_names:
        found = next((a for a in all_adapters if name in a.name), None)
        if found:
            adapter_ids.append(found.device_id)
        else:
            logger.warning(f"Adapter not found: {name}")

    if not adapter_ids:
        logger.error("No valid adapters found")
        return False

    # Toggle all found adapters
    try:
        network_manager.toggle_adapters(
            adapter_ids=adapter_ids,
            enable=False,
            wait=True
        )
        logger.info(f"Toggled {len(adapter_ids)} adapters")
        return True
    except NetworkAdapterError as e:
        logger.error(f"Failed to toggle adapters: {e}")
        return False
```

---

### Pattern 3: Retry with Custom Timeout

```python
def disable_network_with_retry(adapter_ids: list[str], retries: int = 2):
    """Disable network with retry logic and increasing timeouts."""

    base_timeout = 5.0

    for attempt in range(retries):
        timeout = base_timeout * (attempt + 1)  # 5s, 10s, 15s, ...

        try:
            network_manager.toggle_adapters(
                adapter_ids=adapter_ids,
                enable=False,
                wait=True,
                timeout=timeout
            )
            logger.info(f"Network disabled (attempt {attempt + 1})")
            return True

        except NetworkAdapterError as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt == retries - 1:
                logger.error("All retry attempts exhausted")
                raise

    return False
```

---

## Error Handling

### Handling NetworkAdapterError

```python
from autoraid.exceptions import NetworkAdapterError

try:
    network_manager.toggle_adapters(
        adapter_ids=[adapter_id],
        enable=False,
        wait=True,
        timeout=5.0
    )
except NetworkAdapterError as e:
    # Error message format: "Timeout waiting for network to be {online|offline} after {timeout}s"
    logger.error(f"Network timeout: {e}")

    # Option 1: Re-raise for caller to handle
    raise

    # Option 2: Continue with degraded functionality
    logger.warning("Continuing without network disable")

    # Option 3: Retry with longer timeout
    network_manager.toggle_adapters(
        adapter_ids=[adapter_id],
        enable=False,
        wait=True,
        timeout=15.0  # Try again with longer timeout
    )
```

### Handling Invalid Adapter IDs

```python
# The service logs warnings automatically but continues with valid IDs
adapter_ids = ["invalid-id", "{GUID-valid}"]

success = network_manager.toggle_adapters(
    adapter_ids=adapter_ids,  # Mix of invalid + valid
    enable=False,
    wait=True
)

# Logs output:
# WARNING: Invalid adapter ID: invalid-id
# INFO: Toggled adapter {GUID-valid}

if success:
    print("At least one adapter toggled successfully")
else:
    print("All adapter IDs were invalid")
```

---

## Migration Guide

### Step 1: Identify Manual Waiting Loops

Search for code patterns like:
- `while True:` or `for _ in range(...)` after `toggle_adapter()`
- Manual `time.sleep()` calls
- Manual timeout tracking with `time.time()`
- Manual `check_network_access()` calls in loops

### Step 2: Replace with wait=True

**Before**:
```python
network_manager.toggle_adapters(ids, enable=False)
# ... manual waiting loop (10-15 lines) ...
```

**After**:
```python
network_manager.toggle_adapters(ids, enable=False, wait=True)
```

### Step 3: Update Error Handling

**Before**:
```python
if time.time() - start_time > timeout:
    raise NetworkAdapterError("Custom timeout message")
```

**After**:
```python
# NetworkAdapterError raised automatically with standardized message
try:
    network_manager.toggle_adapters(ids, enable=False, wait=True)
except NetworkAdapterError:
    # Handle timeout
```

### Step 4: Update Tests

**Before** (testing manual waiting):
```python
with patch.object(network_manager, 'check_network_access', return_value=False):
    # Test manual waiting loop logic
```

**After** (testing wait=True):
```python
with patch.object(network_manager, 'wait_for_network_state'):
    network_manager.toggle_adapters(ids, enable=False, wait=True)
    network_manager.wait_for_network_state.assert_called_once_with(
        expected_online=False,
        timeout=5.0
    )
```

---

## Constants Reference

```python
# Default timeouts (configurable via timeout parameter)
NetworkManager.DEFAULT_DISABLE_TIMEOUT = 5.0   # seconds
NetworkManager.DEFAULT_ENABLE_TIMEOUT = 10.0   # seconds

# Check interval (not configurable)
NetworkManager.CHECK_INTERVAL = 0.5  # seconds between connectivity checks
```

**When to override defaults**:
- Slow network adapters (increase timeout)
- Fast network adapters (decrease timeout for faster feedback)
- Special hardware requirements

---

## Troubleshooting

### Problem: "Timeout waiting for network to be offline"

**Possible Causes**:
1. Multiple network paths exist (e.g., WiFi + Ethernet both enabled)
2. VPN or virtual adapters providing connectivity
3. Timeout too short for adapter hardware

**Solutions**:
```python
# Solution 1: Disable all network adapters
all_adapter_ids = [a.device_id for a in network_manager.get_adapters()]
network_manager.toggle_adapters(all_adapter_ids, enable=False, wait=True)

# Solution 2: Increase timeout for slow adapters
network_manager.toggle_adapters(ids, enable=False, wait=True, timeout=15.0)

# Solution 3: Check for warnings about multiple paths
# Look for log: "Internet still accessible via other network paths"
```

---

### Problem: "All adapter IDs were invalid"

**Possible Causes**:
1. Incorrect adapter ID format
2. Adapter removed or changed since list query
3. Insufficient permissions (not running as admin)

**Solutions**:
```python
# Solution 1: Re-query adapters (may have changed)
adapters = network_manager.get_adapters()
adapter_ids = [a.device_id for a in adapters]

# Solution 2: Validate IDs before toggling
valid_ids = [a.device_id for a in network_manager.get_adapters()]
filtered_ids = [id for id in requested_ids if id in valid_ids]

if not filtered_ids:
    logger.error("No valid adapter IDs found")
else:
    network_manager.toggle_adapters(filtered_ids, enable=False, wait=True)

# Solution 3: Ensure running with admin rights (required for WMI operations)
```

---

## Performance Notes

- **Non-blocking mode** (`wait=False`): <100ms (just WMI toggle operations)
- **Blocking mode** (`wait=True`): Up to configured timeout (5s/10s defaults)
- **Stability checks**: Adds 0.5s minimum (2 checks × 0.5s interval)
- **Check interval**: 0.5s between connectivity checks (not configurable)
- **Multiple adapters**: Sequential toggling (N adapters × ~100ms each)

---

## Next Steps

1. **Review service contract**: See [contracts/network-manager-service.md](contracts/network-manager-service.md) for full API documentation
2. **Review data model**: See [data-model.md](data-model.md) for entity structures
3. **Review tests**: See test examples in technical plan (plans/nw-technical.md)
4. **Migrate workflows**: Update UpgradeOrchestrator to use new `wait=True` pattern
5. **Update CLI commands**: Move display logic from old display methods to CLI layer

---

## Further Reading

- **Feature Spec**: [spec.md](spec.md) - User scenarios and requirements
- **Implementation Plan**: [plan.md](plan.md) - Technical context and constitution check
- **Research**: [research.md](research.md) - Design decisions and alternatives
- **Service Contract**: [contracts/network-manager-service.md](contracts/network-manager-service.md) - Full API reference
- **Technical Plan**: plans/nw-technical.md (repo root) - Implementation details and test patterns
