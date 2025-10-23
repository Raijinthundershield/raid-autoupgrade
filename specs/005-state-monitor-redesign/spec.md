# Feature Specification: State Monitor Redesign

**Feature Branch**: `005-state-monitor-redesign`
**Created**: 2025-10-23
**Status**: Draft
**Input**: User description: "plans/sm-functional.md"

## Clarifications

### Session 2025-10-23

- Q: Should the progress bar detector return UNKNOWN state or raise an exception when given a null/empty image? → A: Raise exception (InvalidInputError or similar)
- Q: Should the refactored components replace the current state machine in a single atomic change, or should there be a migration period where both implementations coexist? → A: Atomic replacement - Remove old state machine and integrate new components in single change
- Q: What is the maximum acceptable latency for a single state detection call? → A: No performance requirements
- Q: Should state transitions and stop conditions be logged for debugging/operational visibility? → A: Log state transitions and stop conditions at DEBUG level
- Q: How should the monitor receive state updates from the detector? → A: Monitor pulls states using the detector

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Progress Bar State Detection (Priority: P1)

As a developer maintaining AutoRaid, I need the system to accurately identify the current state of the progress bar from a screenshot so that upgrade workflows can respond appropriately to each state.

**Why this priority**: State detection is the foundation of all upgrade workflows. Without accurate state detection, the system cannot count failures or determine when to stop monitoring.

**Independent Test**: Can be fully tested by providing sample progress bar images in each state (FAIL, PROGRESS, STANDBY, CONNECTION_ERROR, UNKNOWN) and verifying the detector returns the correct state for each image. Delivers immediate value by enabling verification of color detection accuracy without running full workflows.

**Acceptance Scenarios**:

1. **Given** a progress bar image showing a red bar, **When** the detector analyzes the image, **Then** it returns state FAIL
2. **Given** a progress bar image showing a yellow bar, **When** the detector analyzes the image, **Then** it returns state PROGRESS
3. **Given** a progress bar image showing a black bar, **When** the detector analyzes the image, **Then** it returns state STANDBY
4. **Given** a progress bar image showing a blue bar, **When** the detector analyzes the image, **Then** it returns state CONNECTION_ERROR
5. **Given** a progress bar image that doesn't match known color patterns, **When** the detector analyzes the image, **Then** it returns state UNKNOWN
6. **Given** the same progress bar image analyzed multiple times, **When** the detector processes it repeatedly, **Then** it returns the same state each time (stateless behavior)

---

### User Story 2 - Upgrade Failure Counting (Priority: P2)

As a user running the Count workflow, I need the system to accurately count upgrade failures so that I know how many attempts are needed before a guaranteed success.

**Why this priority**: Failure counting is the core value proposition of the Count workflow, but depends on state detection working correctly first.

**Independent Test**: Can be fully tested by simulating a sequence of state transitions (e.g., STANDBY → PROGRESS → FAIL → STANDBY → PROGRESS → FAIL) and verifying the monitor counts exactly 2 failures. Delivers value by enabling verification of counting logic with mock state data.

**Acceptance Scenarios**:

1. **Given** the monitor starts with 0 failures, **When** it receives state sequence STANDBY → PROGRESS → FAIL, **Then** the failure count is 1
2. **Given** the monitor has counted 3 failures, **When** it receives another FAIL state after a non-FAIL state, **Then** the failure count becomes 4
3. **Given** the monitor receives consecutive FAIL states, **When** counting failures, **Then** it counts only the first transition to FAIL (not consecutive FAIL states)
4. **Given** the monitor receives state PROGRESS or STANDBY, **When** counting failures, **Then** the failure count remains unchanged

---

### User Story 3 - Automatic Stop Condition Detection (Priority: P3)

As a user running either Count or Spend workflow, I need the system to automatically stop monitoring when a terminal condition is reached so that workflows complete without manual intervention.

**Why this priority**: Automatic stopping improves user experience but requires both detection and counting to work first.

**Independent Test**: Can be fully tested by simulating state sequences that trigger each stop condition and verifying the monitor reports the correct reason. Delivers value by enabling verification of workflow completion logic independently.

**Acceptance Scenarios**:

1. **Given** the monitor is configured with max_attempts=10 and has counted 10 failures, **When** checking stop conditions, **Then** it indicates stopping with reason MAX_ATTEMPTS_REACHED
2. **Given** the monitor receives 4 consecutive STANDBY states, **When** checking stop conditions, **Then** it indicates stopping with reason SUCCESS (upgrade succeeded)
3. **Given** the monitor receives 4 consecutive CONNECTION_ERROR states, **When** checking stop conditions, **Then** it indicates stopping with reason CONNECTION_ERROR
4. **Given** the monitor receives only 3 consecutive STANDBY states, **When** checking stop conditions, **Then** it indicates the workflow should continue (not stopped)

---

### Edge Cases

- What happens when the progress bar image is corrupted or unreadable? (Detector should return UNKNOWN)
- How does the monitor handle receiving UNKNOWN states? (Should not count as failures, should not contribute to stop conditions)
- What happens if the detector receives an empty or null image? (Detector must raise an exception for invalid input - this indicates a programming error in the caller)
- How does the monitor distinguish between the first FAIL and subsequent consecutive FAILs? (Should track previous state to detect transitions)
- What happens if max_attempts is set to 0 or a negative number? (Should validate configuration and reject invalid values)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a progress bar state detector that analyzes a single image and returns one of five states: FAIL, PROGRESS, STANDBY, CONNECTION_ERROR, or UNKNOWN
- **FR-002**: State detector MUST raise an exception when given null or empty image input (invalid input indicates programming error, not runtime condition)
- **FR-003**: State detector MUST be stateless (no memory between detections, same image always returns same state)
- **FR-004**: State detector MUST use the existing color detection algorithm with unchanged color thresholds (b<70, g<90, r>130 for FAIL; b<70, abs(r-g)<50 for PROGRESS; b<30, g<60, r<70 for STANDBY; b>g, b>r, b>50 for CONNECTION_ERROR)
- **FR-005**: System MUST provide an upgrade attempt monitor that tracks failure counts and decides when to stop monitoring
- **FR-006**: Monitor MUST pull states from the detector (monitor calls detector to get current state rather than having states pushed to it)
- **FR-007**: Monitor MUST accept a maximum attempts parameter and stop when that number of failures is reached
- **FR-008**: Monitor MUST count failures only on transitions from any non-FAIL state to FAIL state (not consecutive FAIL states)
- **FR-009**: Monitor MUST track the last 4 states observed to detect stop conditions
- **FR-010**: Monitor MUST stop with reason SUCCESS when 4 consecutive STANDBY states are observed
- **FR-011**: Monitor MUST stop with reason CONNECTION_ERROR when 4 consecutive CONNECTION_ERROR states are observed
- **FR-012**: Monitor MUST stop with reason MAX_ATTEMPTS_REACHED when the configured maximum failures are counted
- **FR-013**: Monitor MUST maintain current state, failure count, and recent state history as internal state
- **FR-014**: System MUST rename "StopCountReason" enum to "StopReason" since it applies to both Count and Spend workflows
- **FR-015**: State detector and monitor MUST be independently testable (detector with image fixtures, monitor with simulated state sequences)
- **FR-016**: Existing Count and Spend workflows MUST continue to function with identical behavior after the redesign
- **FR-017**: Refactored components MUST replace the current state machine in a single atomic change (no dual implementation maintenance period)
- **FR-018**: Monitor MUST log state transitions at DEBUG level for operational visibility (e.g., "State transition: STANDBY → PROGRESS")
- **FR-019**: Monitor MUST log stop conditions at DEBUG level when monitoring terminates (e.g., "Stopping: MAX_ATTEMPTS_REACHED after 10 failures")

### Key Entities

- **ProgressBarState**: Enumeration representing the five possible states of the progress bar (FAIL, PROGRESS, STANDBY, CONNECTION_ERROR, UNKNOWN)
- **ProgressBarDetector**: Component that analyzes a progress bar image and returns a ProgressBarState (stateless, no internal memory)
- **UpgradeAttemptMonitor**: Component that pulls ProgressBarState values from the detector, maintains failure count and state history, and determines when to stop monitoring
- **StopReason**: Enumeration representing why monitoring stopped (MAX_ATTEMPTS_REACHED, SUCCESS, CONNECTION_ERROR) - renamed from "StopCountReason"

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can test state detection logic independently by providing sample images and verifying state output without running full workflows
- **SC-002**: Developers can test failure counting and stop condition logic independently by providing simulated state sequences without using real images
- **SC-003**: The same progress bar image analyzed 100 times returns identical state results 100% of the time (stateless verification)
- **SC-004**: Users experience zero functional changes in Count and Spend workflows (identical failure counts, identical stop behavior, identical error messages)
- **SC-005**: Test coverage for state detection and monitoring logic reaches 90% or higher (inherited from existing state machine coverage requirements)
- **SC-006**: Future modifications to color detection logic require changes only to the detector component, not the monitor
- **SC-007**: Future modifications to stop conditions require changes only to the monitor component, not the detector

## Assumptions

- The existing color detection algorithm is accurate and does not need changes as part of this refactoring
- The existing workflows (Count and Spend) have integration points that can easily swap the refactored components in place of the current state machine
- Test fixtures with sample progress bar images for each state are available or can be easily created from existing test data
- The current state machine code has sufficient test coverage to verify behavior parity after refactoring
- No new performance requirements introduced - refactoring maintains existing detection latency characteristics
