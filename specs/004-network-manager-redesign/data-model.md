# Data Model: NetworkManager Service Redesign

**Feature**: NetworkManager Service Redesign
**Date**: 2025-10-22
**Phase**: 1 (Design & Contracts)

## Overview

This feature is a service refactoring with minimal data model changes. The core entities (Network Adapter, Network State, Timeout Configuration) exist as runtime concepts in the service layer, not as persistent data structures. This document describes their structure and relationships for implementation purposes.

## Entities

### 1. NetworkAdapter

**Description**: Represents a physical or virtual network interface managed by Windows WMI. This is a data transfer object (DTO) used by the service to represent adapter information.

**Source**: Windows WMI query results (existing implementation)

**Attributes**:

| Attribute | Type | Required | Description | Validation |
|-----------|------|----------|-------------|------------|
| `device_id` | `str` | Yes | Unique WMI device identifier | Non-empty string |
| `name` | `str` | Yes | Human-readable adapter name | Non-empty string |
| `enabled` | `bool` | Yes | Current adapter state | Boolean |
| `adapter_type` | `str` | No | Adapter type (Ethernet, WiFi, etc.) | Optional string |

**Example**:
```python
NetworkAdapter(
    device_id="{GUID-12345}",
    name="Intel(R) Ethernet Connection",
    enabled=True,
    adapter_type="Ethernet"
)
```

**Lifecycle**: Created on-demand from WMI queries, no persistence

**Relationships**: None (standalone entity)

---

### 2. NetworkState

**Description**: Represents the system's current internet connectivity status. This is a runtime concept, not a persistent entity. The state is determined by connectivity checks (DNS + HTTP fallback).

**States**:

| State | Description | Detection Method |
|-------|-------------|------------------|
| `ONLINE` | Internet connectivity available | DNS check (8.8.8.8:53) succeeds OR HTTP fallback succeeds |
| `OFFLINE` | No internet connectivity | DNS check fails AND HTTP fallback fails |

**State Transitions**:
```
┌─────────┐
│ ONLINE  │ ◄──► enable adapters + wait
└─────────┘
     │
     ▼ disable adapters + wait
┌─────────┐
│ OFFLINE │
└─────────┘
```

**Stability Requirement**: State must be consistent for 2 consecutive checks before confirming (prevents transient flickers)

**Lifecycle**: Checked on-demand via `check_network_access()`, no persistence

**Relationships**: Affected by NetworkAdapter enabled/disabled state (but not directly coupled)

---

### 3. TimeoutConfiguration

**Description**: Encapsulates timeout values for network state change operations. Not a persistent entity - embedded in NetworkManager as class constants.

**Attributes**:

| Attribute | Type | Default | Description | Validation |
|-----------|------|---------|-------------|------------|
| `DEFAULT_DISABLE_TIMEOUT` | `float` | `5.0` | Seconds to wait for network to go offline | > 0 |
| `DEFAULT_ENABLE_TIMEOUT` | `float` | `10.0` | Seconds to wait for network to come online | > 0 |
| `CHECK_INTERVAL` | `float` | `0.5` | Seconds between connectivity checks | > 0 |

**Rationale for Defaults**:
- **5s disable**: Adapters typically disable quickly (<1s), 5s provides generous buffer
- **10s enable**: Adapters may need DHCP negotiation, 10s accommodates slower networks
- **0.5s check interval**: Balances responsiveness vs polling overhead

**Override Capability**: Callers can override timeout via `timeout` parameter in `toggle_adapters()`

**Example**:
```python
# Use defaults
manager.toggle_adapters(ids, enable=False, wait=True)  # Uses 5s timeout

# Override timeout
manager.toggle_adapters(ids, enable=False, wait=True, timeout=15.0)  # Uses 15s
```

**Lifecycle**: Class constants in NetworkManager, instantiated once with service

---

### 4. ToggleOperation (Implicit)

**Description**: Represents a network adapter toggle request with waiting behavior. This is not a formal entity/class, but a conceptual model for understanding operation semantics.

**Attributes**:

| Attribute | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `adapter_ids` | `list[str]` | Yes | Adapter device IDs to toggle | N/A |
| `enable` | `bool` | Yes | True=enable, False=disable | N/A |
| `wait` | `bool` | No | Block until state change confirmed | `False` |
| `timeout` | `float \| None` | No | Custom timeout (None=use defaults) | `None` |

**Operation States**:
```
┌──────────────┐
│   PENDING    │ ──► toggle_adapters() called
└──────────────┘
       │
       ▼ loop: toggle each adapter
┌──────────────┐
│  TOGGLING    │ ──► calling toggle_adapter(id, enable) for each ID
└──────────────┘
       │
       ▼ if wait=True
┌──────────────┐
│   WAITING    │ ──► wait_for_network_state(expected_online, timeout)
└──────────────┘
       │
       ├─► success: state matches expected (after 2 consecutive checks)
       │   ┌──────────────┐
       │   │   SUCCESS    │
       │   └──────────────┘
       │
       └─► failure: timeout exceeded
           ┌──────────────┐
           │    ERROR     │ ──► NetworkAdapterError raised
           └──────────────┘
```

**Edge Case Handling** (from clarifications):

| Condition | Behavior | State |
|-----------|----------|-------|
| All adapter IDs invalid | Log warnings, return False | ERROR |
| Some adapter IDs invalid | Log warnings, continue with valid | SUCCESS (if ≥1 valid) |
| No adapters available | Succeed silently (no-op) | SUCCESS |
| Internet remains after disable | Log warning, continue | SUCCESS (with warning) |
| State oscillates | Reset consecutive check counter | WAITING (extended) |

---

## Entity Relationships

```
NetworkManager (Service)
│
├─► manages ──► NetworkAdapter (1..N)
│                   └─► state: enabled/disabled
│
├─► checks ──► NetworkState (runtime)
│                   └─► states: ONLINE / OFFLINE
│
└─► uses ──► TimeoutConfiguration (class constants)
                    └─► values: disable=5s, enable=10s, interval=0.5s
```

**Key Relationships**:
- NetworkManager **queries** NetworkAdapters from WMI (1-to-many)
- NetworkManager **toggles** NetworkAdapter state (enabled ↔ disabled)
- NetworkManager **checks** NetworkState via connectivity test
- NetworkAdapter state changes **affect** NetworkState (but indirect - depends on network topology)
- TimeoutConfiguration **constrains** wait operations in NetworkManager

---

## State Validation Rules

### NetworkAdapter Validation

- `device_id` must be non-empty string
- `name` must be non-empty string
- `enabled` must be boolean
- Invalid adapter IDs → log warning, skip (graceful degradation per clarification Q2)

### NetworkState Validation

- State determined by connectivity check result (boolean)
- Requires 2 consecutive matching checks before confirming (per clarification Q3)
- No direct validation needed (derived from network connectivity)

### TimeoutConfiguration Validation

- All timeout values must be positive floats (> 0)
- `CHECK_INTERVAL` must be less than timeout values (otherwise: no checks before timeout)
- Custom timeout values validated at runtime (implicit: must be positive)

---

## Data Flow

### Toggle with Wait Flow

```
1. toggle_adapters(["adapter1", "adapter2"], enable=False, wait=True)
   │
   ├─► Validate: filter invalid adapter IDs (log warnings)
   │
   ├─► Toggle: for each valid ID
   │   └─► toggle_adapter(id, enable=False)
   │       └─► WMI call to disable adapter
   │           └─► NetworkAdapter.enabled = False
   │
   ├─► Wait: wait_for_network_state(expected_online=False, timeout=5.0)
   │   │
   │   └─► Loop until timeout:
   │       ├─► Sleep CHECK_INTERVAL (0.5s)
   │       ├─► Check: check_network_access()
   │       │   └─► DNS query + HTTP fallback
   │       │       └─► Returns: NetworkState (ONLINE/OFFLINE)
   │       │
   │       ├─► If state matches expected:
   │       │   └─► Increment consecutive check counter
   │       │       └─► If counter >= 2: RETURN SUCCESS
   │       │
   │       ├─► If state doesn't match:
   │       │   └─► Reset consecutive check counter to 0
   │       │
   │       └─► If elapsed >= timeout:
   │           └─► RAISE NetworkAdapterError
   │
   └─► Check: If still online after disable
       └─► Log warning: "Internet still accessible via other network paths"
```

---

## Persistence

**None** - This feature operates entirely on runtime state:
- NetworkAdapter data comes from WMI queries (Windows OS state)
- NetworkState is checked on-demand (network connectivity)
- TimeoutConfiguration is hardcoded as class constants
- No database, no files, no cache writes for this feature

**Existing Cache** (not modified by this feature):
- AutoRaid's diskcache stores region screenshots, not network state
- Cache service unchanged by this refactoring

---

## Summary

**Core Entities**: 3 runtime concepts (NetworkAdapter, NetworkState, TimeoutConfiguration)
**Relationships**: NetworkManager orchestrates toggling and waiting
**Persistence**: None (all runtime state from OS/network)
**Validation**: Minimal (graceful degradation for invalid inputs per clarifications)

This data model represents the conceptual structure for implementation, not a persistent schema. All state is derived from Windows WMI (adapters) and network connectivity checks (state).
