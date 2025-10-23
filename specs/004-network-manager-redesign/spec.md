# Feature Specification: NetworkManager Service Redesign

**Feature Branch**: `004-network-manager-redesign`
**Created**: 2025-10-22
**Status**: Draft
**Input**: User description: "plans/nw-functional.md"

## Clarifications

### Session 2025-10-22

- Q: When disabling specified adapters, if the system still has internet via other adapters/paths, should the operation consider the network "offline" for the purpose of completing successfully? → A: Report a warning/error if internet remains accessible after disabling specified adapters
- Q: What should happen when an invalid or non-existent adapter ID is provided to a network toggle operation? → A: Log a warning but continue with valid adapters only
- Q: When waiting for network to go offline, if the connectivity flickers (goes offline briefly then returns), should the operation succeed or continue waiting? → A: Require sustained offline status for 2 consecutive checks by default before succeeding
- Q: Should the system support toggling multiple adapters in a single operation call, or should it handle multiple adapters sequentially/individually? → A: Support multiple adapter IDs in a single operation (toggle all specified adapters together)
- Q: What should happen when a network toggle operation is requested but no network adapters are available or accessible on the system? → A: Silently succeed (treat as no-op since there's nothing to toggle)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Simplified Network Toggle with Automatic Waiting (Priority: P1)

As a developer using the upgrade workflow, I want to disable network adapters and have the system automatically wait for the network to go offline, so that I don't need to write manual waiting logic with timeouts and error handling in every workflow.

**Why this priority**: This is the core value proposition of the redesign - eliminating duplicated waiting logic across workflows. It directly solves the main problem identified in the current system.

**Independent Test**: Can be fully tested by requesting a network disable operation with automatic waiting, and verifying that the operation only completes when the network is confirmed offline (or fails with a timeout error). Delivers immediate value by simplifying the most common use case.

**Acceptance Scenarios**:

1. **Given** the system has network access, **When** a network disable operation with automatic waiting is requested, **Then** the system disables the specified adapters, waits until network access is confirmed offline, and completes successfully
2. **Given** the system has network access, **When** a network disable operation with automatic waiting is requested and the network fails to go offline within the timeout period, **Then** the system reports a timeout error with a descriptive message
3. **Given** the network is already offline, **When** a network disable operation with automatic waiting is requested, **Then** the system completes immediately without unnecessary waiting
4. **Given** the network is offline, **When** a network enable operation with automatic waiting is requested, **Then** the system enables the adapters, waits until network access is confirmed online, and completes successfully

---

### User Story 2 - Non-blocking Network Toggle for Cleanup (Priority: P2)

As a developer implementing error handling and cleanup logic, I want to re-enable network adapters without waiting for confirmation, so that my cleanup operations can execute quickly without blocking on network state changes.

**Why this priority**: Critical for proper error handling and cleanup patterns, but less common than the primary toggle-and-wait use case. Enables non-blocking operations when waiting isn't required.

**Independent Test**: Can be fully tested by requesting a non-blocking network enable operation and verifying that the operation completes immediately after initiating the enable, without waiting for network to come online.

**Acceptance Scenarios**:

1. **Given** the network is offline, **When** a non-blocking network enable operation is requested, **Then** the system initiates the enable operation and completes immediately without waiting for network confirmation
2. **Given** a workflow encounters an error, **When** cleanup operations request a non-blocking network enable, **Then** the network adapters are re-enabled without blocking the error handling flow

---

### User Story 3 - Configurable Timeout Overrides (Priority: P3)

As a developer working with specific network environments or hardware, I want to override the default timeout values for network state changes, so that I can accommodate slower or faster network adapters without modifying system configuration.

**Why this priority**: Provides flexibility for edge cases and non-standard environments, but the default timeouts should work for most scenarios. Optional enhancement that doesn't block core functionality.

**Independent Test**: Can be fully tested by requesting a network operation with a custom timeout value and verifying that the system uses the custom timeout instead of the default.

**Acceptance Scenarios**:

1. **Given** I need a longer timeout for my network adapter, **When** I request a disable operation with a 15-second timeout, **Then** the system waits up to 15 seconds instead of the default timeout
2. **Given** I have a fast network adapter, **When** I request an enable operation with a 3-second timeout, **Then** the system waits up to 3 seconds instead of the default timeout

---

### Edge Cases

- **Multiple network paths**: When specified adapters are disabled but internet remains accessible via other adapters/paths, the system MUST report a warning or error to indicate the network is not fully offline
- **Invalid adapter IDs**: When invalid or non-existent adapter IDs are provided, the system MUST log a warning and continue operating on valid adapter IDs only
- **Oscillating network state**: When waiting for network state changes, the system MUST verify stable state by requiring 2 consecutive successful checks before completing the operation (prevents false positives from transient connectivity flickers)
- **Multiple adapter operations**: The system MUST support toggling multiple adapter IDs in a single operation call, processing all specified adapters together
- **No adapters available**: When no network adapters are available or accessible on the system, operations MUST succeed silently as a no-op (nothing to toggle)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a unified operation that accepts one or more adapter identifiers, enable/disable instruction, and optional automatic waiting behavior
- **FR-002**: System MUST encapsulate all waiting logic within network toggle operations when automatic waiting is requested
- **FR-003**: System MUST use default timeout values of 5 seconds for disable operations and 10 seconds for enable operations
- **FR-004**: System MUST allow developers to override default timeout values when requesting network operations
- **FR-005**: System MUST report a descriptive timeout error when a network state change does not complete within the specified timeout
- **FR-006**: System MUST complete immediately when non-blocking operation mode is specified, without waiting for network state confirmation
- **FR-007**: System MUST verify network state by checking actual internet connectivity (not just adapter status) when automatic waiting is requested
- **FR-012**: System MUST report a warning or error when internet connectivity remains after disabling specified adapters (indicating other network paths exist)
- **FR-013**: System MUST log a warning when invalid or non-existent adapter IDs are provided, then continue operating on valid adapter IDs only
- **FR-014**: System MUST verify stable network state by requiring 2 consecutive successful connectivity checks (with the expected state) before completing waiting operations
- **FR-015**: System MUST treat operations as successful no-ops when no network adapters are available or accessible on the system
- **FR-008**: Core network management functionality MUST NOT contain any display or formatting logic
- **FR-009**: User interface layers MUST handle all interactive features and display formatting, accessing network management capabilities via service interfaces
- **FR-010**: All application layers MUST access network management functionality through consistent service interfaces
- **FR-011**: Existing adapter listing and connectivity checking capabilities MUST remain available for use by all application layers

### Key Entities

- **Network Adapter**: Represents a physical or virtual network interface that can be enabled/disabled. Key attributes include adapter ID, name, and current state (enabled/disabled).
- **Network State**: Represents the system's current internet connectivity status (online/offline), independent of individual adapter states.
- **Timeout Configuration**: Represents the maximum time to wait for a network state change, with different defaults for enable vs disable operations.

## Dependencies and Assumptions

### Dependencies

- Existing network adapter management capabilities (enable/disable operations)
- Internet connectivity verification mechanism
- Current service architecture and interface contracts
- All existing workflows that use network adapter toggling

### Assumptions

- Default timeout values (5s disable, 10s enable) are sufficient for standard network adapter hardware
- Internet connectivity check is a reliable indicator of network state (not just adapter status)
- Network state transitions are deterministic within reasonable timeout windows
- Existing workflows can be refactored to use the new unified operation without breaking user-visible behavior
- The system has at least one controllable network adapter when network management features are used

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can toggle network adapters with automatic waiting using a single operation, reducing code duplication by 100% (eliminating manual waiting loops in all 3+ existing workflows)
- **SC-002**: Network toggle operations complete within the specified timeout (5s for disable, 10s for enable) or fail with a clear error message in 100% of test cases
- **SC-003**: Core network management functionality passes all tests without requiring any display or formatting dependencies
- **SC-004**: All existing user-facing commands and interface panels continue to function identically after the redesign, with no behavioral changes visible to end users (100% backward compatibility)
- **SC-005**: Non-blocking operations complete within 100 milliseconds without waiting for network state verification
- **SC-006**: Error messages for timeout failures clearly identify which operation failed (enable/disable) and the timeout duration used in 100% of error cases
