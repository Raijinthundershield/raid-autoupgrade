# Deep Analysis: Why ProgressBarMonitor and UpgradeOrchestrator Should NOT Be Injected

## Executive Summary

After deeper analysis, **both ProgressBarMonitor and UpgradeOrchestrator should be removed from the DI container**. While they appear to be legitimate services at first glance, they violate fundamental DI principles:

1. **ProgressBarMonitor**: Stateful per-session object with zero reusability (created once per orchestrator, used for one session)
2. **UpgradeOrchestrator**: Effectively one-shot per workflow (created once per workflow, used for one session)

Both are **application-layer coordination logic**, not infrastructure services. They should be constructed directly with explicit dependencies.

---

## Part 1: ProgressBarMonitor Analysis

### Current Implementation

```python
# Container
progress_bar_monitor = providers.Factory(
    ProgressBarMonitor,
    detector=progress_bar_detector,
)

# Orchestrator receives injected monitor
class UpgradeOrchestrator:
    def __init__(self, ..., monitor: ProgressBarMonitor):
        self._monitor = monitor
```

### Usage Pattern Analysis

**Question**: How many times is a single ProgressBarMonitor instance used?

**Answer**: Exactly **once** - for a single `run_upgrade_session()` call.

**Evidence from code:**

```python
# upgrade_orchestrator.py:176-177
current_state = self._monitor.process_frame(upgrade_bar_roi)
monitor_state = self._monitor.get_state()

# upgrade_orchestrator.py:130
final_state = self._monitor.get_state()  # After loop completes
```

**Lifecycle:**
1. Orchestrator created with fresh monitor
2. `run_upgrade_session()` called
3. Monitor processes frames in `_monitor_loop()`
4. Session ends, final state extracted
5. **Monitor state is never reused** (orchestrator discarded after workflow completes)

### Constitutional Violations

#### 1. **YAGNI Violation: Unnecessary Factory Pattern**

**Why use Factory?**
- Monitor has **stateful per-session behavior** (fail_count, frames_processed, recent_states)
- Each session needs fresh monitor with reset state
- Factory pattern allows multiple instances

**Why this violates YAGNI:**
- Orchestrator is **also a Factory** (created per workflow)
- Each orchestrator gets **exactly one monitor**
- Monitor is **never reused** across sessions
- Factory pattern provides **zero benefit** over direct construction

**Simpler alternative:**
```python
# Orchestrator creates monitor directly when needed
class UpgradeOrchestrator:
    def __init__(self, ..., detector: ProgressBarStateDetector):
        self._detector = detector  # Store detector, not monitor

    def run_upgrade_session(self, session):
        monitor = ProgressBarMonitor(self._detector)  # Fresh per session
        # ... use monitor
```

#### 2. **Simplicity Over Complexity: Double Factory Indirection**

**Current complexity:**
```
Container
├── progress_bar_monitor (Factory)
│   └── Creates new ProgressBarMonitor
└── upgrade_orchestrator (Factory)
    └── Receives progress_bar_monitor (Factory)
        └── Which creates new ProgressBarMonitor

Workflow creates orchestrator → Orchestrator receives monitor → Monitor used once
```

**Simplified:**
```
Container
└── progress_bar_detector (Singleton)

Workflow creates orchestrator → Orchestrator creates monitor → Monitor used once
```

**Benefit:** One less factory layer, same functionality.

#### 3. **Explicit Over Implicit: Hidden Monitor Creation**

**Current (implicit):**
```python
# User has no idea a monitor is being created
orchestrator = container.upgrade_orchestrator()
```

**Proposed (explicit):**
```python
# Clear that orchestrator needs detector to create monitors
orchestrator = UpgradeOrchestrator(
    screenshot_service=...,
    window_service=...,
    detector=detector,  # Explicit: "I'll use this to create monitors"
)
```

### Testing Impact Analysis

**Claim**: "Injecting monitor enables testing orchestrator without CV"

**Reality**: Tests already construct orchestrator with mocked monitor:

```python
# test_upgrade_orchestrator.py:42-48
mock_monitor = Mock(spec=ProgressBarMonitor)

orchestrator = UpgradeOrchestrator(
    screenshot_service=mock_screenshot,
    window_interaction_service=mock_window,
    cache_service=mock_cache,
    network_manager=mock_network,
    monitor=mock_monitor,  # Mocked, not from container
)
```

**Proposed change:**
```python
# Inject detector instead of monitor
mock_detector = Mock(spec=ProgressBarStateDetector)

orchestrator = UpgradeOrchestrator(
    screenshot_service=mock_screenshot,
    window_interaction_service=mock_window,
    cache_service=mock_cache,
    network_manager=mock_network,
    detector=mock_detector,  # Mock detector, orchestrator creates monitor
)
```

**Testing impact**: **Zero** - tests still mock dependencies, just at detector level instead of monitor level.

### Reusability Analysis

**Question**: Is ProgressBarMonitor reused across different contexts?

**Answer**: **No**. Monitor is used in exactly one place: `UpgradeOrchestrator._monitor_loop()`.

**Evidence:**
```bash
$ grep -r "ProgressBarMonitor" src/autoraid --include="*.py" | grep -v "import\|test"
src/autoraid/services/upgrade_orchestrator.py:        monitor: ProgressBarMonitor,
```

**Only usage**: As dependency in UpgradeOrchestrator.

**Conclusion**: Monitor is **not a reusable service** - it's a **stateful helper object** for orchestrator.

### Polymorphism Analysis

**Question**: Will we ever swap ProgressBarMonitor for alternative implementations?

**Answer**: **Extremely unlikely**.

**Why?**
- Monitor logic is simple: track state transitions, count fails
- Business logic is specific to AutoRaid's progress bar detection
- No reason to have multiple implementations (AlternativeProgressBarMonitor?)

**If we DID need polymorphism:**
- Could use protocol/interface (`IProgressBarMonitor`)
- Still wouldn't need DI container - constructor injection sufficient

**Conclusion**: Polymorphism doesn't justify DI container usage.

### Verdict: ❌ REMOVE ProgressBarMonitor from DI

**Reasons:**
1. **One-shot usage**: Created per session, never reused
2. **Double factory**: Orchestrator already factory, monitor factory redundant
3. **Zero reusability**: Only used by orchestrator
4. **No polymorphism**: Always concrete ProgressBarMonitor
5. **Testing unchanged**: Tests still mock, just at detector level
6. **Simpler alternative**: Direct construction clearer

**Recommendation:**
```python
# Container: Remove monitor factory
# progress_bar_monitor = providers.Factory(...)  # DELETE

# Orchestrator: Inject detector, create monitor
class UpgradeOrchestrator:
    def __init__(
        self,
        screenshot_service: ScreenshotService,
        window_interaction_service: WindowInteractionService,
        cache_service: CacheService,
        network_manager: NetworkManager,
        detector: ProgressBarStateDetector,  # Changed from monitor
    ):
        self._screenshot_service = screenshot_service
        self._window_interaction_service = window_interaction_service
        self._cache_service = cache_service
        self._network_manager = network_manager
        self._detector = detector

    def run_upgrade_session(self, session: UpgradeSession) -> UpgradeResult:
        # Create fresh monitor per session
        monitor = ProgressBarMonitor(self._detector)

        # ... rest of implementation uses monitor
        self._monitor_loop(session, monitor, debug_logger)
```

---

## Part 2: UpgradeOrchestrator Analysis

### Current Implementation

```python
# Container
upgrade_orchestrator = providers.Factory(
    UpgradeOrchestrator,
    screenshot_service=screenshot_service,
    window_interaction_service=window_interaction_service,
    cache_service=cache_service,
    network_manager=network_manager,
    monitor=progress_bar_monitor,  # Factory!
)

# Workflows receive orchestrator factory (after workflows removed from DI)
@inject
def count(
    orchestrator_factory: Callable = Provide[Container.upgrade_orchestrator.provider],
    ...
):
    workflow = CountWorkflow(
        orchestrator=orchestrator_factory(),  # Create orchestrator
        ...
    )
```

### Usage Pattern Analysis

**Question**: How many upgrade sessions does a single orchestrator run?

**Answer**: Exactly **one** in CountWorkflow and DebugMonitorWorkflow. **Multiple** only in SpendWorkflow's multi-iteration loop.

**Evidence:**

**CountWorkflow (one session):**
```python
# count_workflow.py:155
result = self._orchestrator.run_upgrade_session(session)  # Called once
return CountResult(fail_count=result.fail_count, ...)
```

**SpendWorkflow (multiple sessions in loop):**
```python
# spend_workflow.py:106-137
while remaining_attempts > 0:
    session = UpgradeSession(...)
    result = self._orchestrator.run_upgrade_session(session)  # Multiple calls

    # Update counters
    attempt_count += result.fail_count
    remaining_attempts -= result.fail_count

    # Handle stop reasons
    if stop_reason == StopReason.UPGRADED:
        upgrade_count += 1
        if continue_upgrade:
            continue  # Loop again
        else:
            break
```

**DebugMonitorWorkflow (one session):**
```python
# debug_monitor_workflow.py:149
result = self._orchestrator.run_upgrade_session(session)  # Called once
```

**Key Insight**: Only SpendWorkflow reuses orchestrator across multiple sessions. But SpendWorkflow is being **removed from DI** (it shouldn't be injected).

### Post-Workflow-Removal Analysis

**After removing workflows from DI**, how is orchestrator used?

**New usage pattern:**
```python
# CLI/GUI construct workflow directly
@inject
def count(
    cache_service: CacheService = Provide[...],
    window_service: WindowInteractionService = Provide[...],
    network_manager: NetworkManager = Provide[...],
    detector: ProgressBarStateDetector = Provide[...],
):
    # Option 1: Inject orchestrator factory
    orchestrator = container.upgrade_orchestrator()
    workflow = CountWorkflow(orchestrator=orchestrator, ...)

    # Option 2: Construct orchestrator directly
    orchestrator = UpgradeOrchestrator(
        screenshot_service=screenshot_service,
        window_interaction_service=window_service,
        cache_service=cache_service,
        network_manager=network_manager,
        detector=detector,
    )
    workflow = CountWorkflow(orchestrator=orchestrator, ...)
```

**Question**: Does Option 1 (injected factory) provide value over Option 2 (direct construction)?

**Answer**: **No** - it's just indirection without benefit.

### Constitutional Violations

#### 1. **YAGNI Violation: Factory Pattern for One-Shot Objects**

**Orchestrator lifecycle per workflow:**

**CountWorkflow:**
1. Create orchestrator
2. Call `run_upgrade_session()` **once**
3. Discard orchestrator with workflow

**SpendWorkflow:**
1. Create orchestrator
2. Call `run_upgrade_session()` **multiple times in loop**
3. Discard orchestrator with workflow

**Key point**: Even in SpendWorkflow, orchestrator lifetime = workflow lifetime. They're created and destroyed together.

**Why this violates YAGNI:**
- Factory pattern suggests orchestrator is **reusable** across contexts
- Reality: Orchestrator is **1:1 with workflow** (created together, destroyed together)
- No sharing across workflows
- No sharing across CLI invocations
- Factory provides **zero benefit** over direct construction

#### 2. **Simplicity Over Complexity: Triple Indirection**

**Current complexity (after workflow factories removed):**
```
User Action (CLI/GUI)
    ↓
Creates Workflow (direct construction)
    ↓
Workflow receives orchestrator (from container factory)
    ↓
Orchestrator receives monitor (from container factory)
    ↓
Monitor uses detector (singleton)
```

**Proposed simplicity:**
```
User Action (CLI/GUI)
    ↓
Creates Workflow (direct construction)
    ↓
Workflow creates Orchestrator (direct construction)
    ↓
Orchestrator creates Monitor (direct construction)
    ↓
Monitor uses Detector (from container - singleton)
```

**Benefit:**
- Two fewer factory providers in container
- Dependency graph explicit at construction
- Same testability (constructor injection)

#### 3. **Explicit Over Implicit: Hidden Dependency Graph**

**Current (implicit):**
```python
# What dependencies does orchestrator have? Hidden in container!
orchestrator = container.upgrade_orchestrator()
```

**Proposed (explicit):**
```python
# Clear: orchestrator needs these 5 services
orchestrator = UpgradeOrchestrator(
    screenshot_service=screenshot_service,
    window_interaction_service=window_service,
    cache_service=cache_service,
    network_manager=network_manager,
    detector=detector,
)
```

**Benefit**: Dependencies visible at call site, no need to look at container definition.

### Reusability Analysis

**Question**: Is UpgradeOrchestrator reused across different workflows?

**Answer**: **Yes, but not in a way that justifies DI**.

**Usage pattern:**
- CountWorkflow creates orchestrator → uses once
- SpendWorkflow creates orchestrator → uses multiple times **in same workflow instance**
- DebugMonitorWorkflow creates orchestrator → uses once

**Key insight**: Orchestrator is **reused within SpendWorkflow loop**, but not **shared between workflows**.

**Comparison to true shared services:**

| Service | Sharing Pattern | Justifies DI? |
|---------|-----------------|---------------|
| **CacheService** | Shared by ALL workflows, CLI, GUI | ✅ YES |
| **ScreenshotService** | Shared by orchestrator, region service, CLI | ✅ YES |
| **NetworkManager** | Shared by workflows, network CLI/GUI | ✅ YES |
| **UpgradeOrchestrator** | Created per workflow, used by that workflow only | ❌ NO |

**Orchestrator is NOT shared** - it's **owned by one workflow**.

### Testing Impact Analysis

**Claim**: "Injecting orchestrator enables workflow testing without orchestrator implementation"

**Reality**: Workflow tests already mock orchestrator:

```python
# test_count_workflow_integration.py (hypothetical)
def test_count_workflow_with_mocked_orchestrator():
    mock_orchestrator = Mock(spec=UpgradeOrchestrator)
    mock_orchestrator.run_upgrade_session.return_value = UpgradeResult(
        fail_count=5,
        frames_processed=20,
        stop_reason=StopReason.MAX_ATTEMPTS_REACHED,
    )

    workflow = CountWorkflow(
        cache_service=mock_cache,
        window_interaction_service=mock_window,
        network_manager=mock_network,
        orchestrator=mock_orchestrator,  # Mocked, not from container
        network_adapter_ids=None,
        max_attempts=10,
    )

    result = workflow.run()
    assert result.fail_count == 5
```

**Proposed change:**
```python
# Same test, construct orchestrator with mocks instead of mocking orchestrator
def test_count_workflow_with_mocked_services():
    mock_screenshot = Mock(spec=ScreenshotService)
    mock_window = Mock(spec=WindowInteractionService)
    # ... configure mocks

    orchestrator = UpgradeOrchestrator(
        screenshot_service=mock_screenshot,
        window_interaction_service=mock_window,
        cache_service=mock_cache,
        network_manager=mock_network,
        detector=mock_detector,
    )

    workflow = CountWorkflow(
        cache_service=mock_cache,
        window_interaction_service=mock_window,
        network_manager=mock_network,
        orchestrator=orchestrator,  # Real orchestrator with mocked services
        network_adapter_ids=None,
        max_attempts=10,
    )

    result = workflow.run()
    # Verify orchestrator behavior, not mocked results
```

**Testing impact**: **Improved** - tests verify real orchestrator logic instead of mocking it away.

### Polymorphism Analysis

**Question**: Will we ever swap UpgradeOrchestrator for alternative implementations?

**Answer**: **Extremely unlikely**.

**Why?**
- Orchestrator encapsulates AutoRaid-specific upgrade session logic
- Tightly coupled to UpgradeSession/UpgradeResult contracts
- No business reason for multiple implementations

**If we DID need polymorphism:**
- Could use protocol/interface (`IUpgradeOrchestrator`)
- Still wouldn't need DI container - constructor injection sufficient

**Conclusion**: Polymorphism doesn't justify DI container usage.

### Domain Layer Analysis

**Question**: Is UpgradeOrchestrator infrastructure or application logic?

**Answer**: **Application logic** (coordination layer).

**Evidence:**

**Infrastructure services** (reusable, platform abstraction):
- ScreenshotService: "Take screenshot of window"
- WindowInteractionService: "Click region in window"
- CacheService: "Store/retrieve from cache"
- NetworkManager: "Enable/disable network adapters"

**Application/coordination logic** (use-case specific):
- UpgradeOrchestrator: "Run upgrade monitoring session with stop conditions"
- CountWorkflow: "Count fails offline with network disabled"
- SpendWorkflow: "Spend attempts online, tracking upgrades"

**Key difference**: Infrastructure services are **context-free** (don't know about "upgrade session"). Orchestrator is **context-aware** (knows about upgrade flow).

**Principle**: DI containers should manage **infrastructure**, not **application logic**.

### Verdict: ❌ REMOVE UpgradeOrchestrator from DI

**Reasons:**
1. **Effectively one-shot**: Created per workflow, lifetime = workflow lifetime
2. **Not truly shared**: Each workflow gets its own orchestrator
3. **Application layer**: Coordination logic, not infrastructure
4. **No polymorphism**: Always concrete UpgradeOrchestrator
5. **Testing improved**: Test real orchestrator with mocked services
6. **Simpler alternative**: Direct construction clearer, fewer factory layers

**Recommendation:**
```python
# Container: Remove orchestrator factory
# upgrade_orchestrator = providers.Factory(...)  # DELETE

# Workflows construct orchestrator directly
class CountWorkflow:
    def __init__(
        self,
        cache_service: CacheService,
        window_interaction_service: WindowInteractionService,
        network_manager: NetworkManager,
        screenshot_service: ScreenshotService,
        detector: ProgressBarStateDetector,
        network_adapter_ids: list[int] | None = None,
        max_attempts: int = 99,
        debug_dir: Path | None = None,
    ):
        self._cache_service = cache_service
        self._window_interaction_service = window_interaction_service
        self._network_manager = network_manager
        self._screenshot_service = screenshot_service
        self._detector = detector
        self._network_adapter_ids = network_adapter_ids
        self._max_attempts = max_attempts
        self._debug_dir = debug_dir

    def run(self) -> CountResult:
        # Create orchestrator on-demand
        orchestrator = UpgradeOrchestrator(
            screenshot_service=self._screenshot_service,
            window_interaction_service=self._window_interaction_service,
            cache_service=self._cache_service,
            network_manager=self._network_manager,
            detector=self._detector,
        )

        # ... create session, run orchestrator
        result = orchestrator.run_upgrade_session(session)
        return CountResult(...)
```

---

## Part 3: Cascade Analysis - What Happens When We Remove Both?

### Current Dependency Graph

```
Container
├── progress_bar_detector (Singleton)
├── progress_bar_monitor (Factory) ← REMOVE
│   └── depends on: detector
├── upgrade_orchestrator (Factory) ← REMOVE
│   └── depends on: screenshot, window, cache, network, monitor
├── count_workflow_factory (Factory) ← ALREADY BEING REMOVED
│   └── depends on: orchestrator, cache, window, network
└── (other services)
```

### Proposed Dependency Graph

```
Container
├── progress_bar_detector (Singleton)
└── (other services)

Construction at call site:
User Action
    ↓
Workflow (constructed with services)
    ↓
Orchestrator (constructed by workflow)
    ↓
Monitor (constructed by orchestrator)
    ↓
Detector (singleton from container)
```

### Benefits of Full Removal

1. **Simpler Container**
   - Before: 13 providers (8 singletons, 5 factories)
   - After: 8 providers (8 singletons, 0 factories)
   - **62% reduction in factory complexity**

2. **Explicit Dependency Graph**
   ```python
   # All dependencies visible at construction
   detector = container.progress_bar_detector()
   orchestrator = UpgradeOrchestrator(
       screenshot_service=screenshot_service,
       window_interaction_service=window_service,
       cache_service=cache_service,
       network_manager=network_manager,
       detector=detector,
   )
   workflow = CountWorkflow(
       cache_service=cache_service,
       window_interaction_service=window_service,
       network_manager=network_manager,
       screenshot_service=screenshot_service,
       detector=detector,
       network_adapter_ids=adapter_ids,
       max_attempts=99,
   )
   ```

3. **Constitutional Alignment**
   - ✅ **YAGNI**: No unnecessary factory patterns
   - ✅ **Simplicity**: Direct construction, clear dependencies
   - ✅ **Explicit**: All dependencies visible
   - ✅ **Separation**: Container manages infrastructure, application constructs coordination

4. **Testing Benefits**
   - Test real orchestrator with mocked services (better coverage)
   - Test real monitor with mocked detector (better coverage)
   - No factory mocking complexity

### Risks of Removal

#### Risk 1: "Boilerplate increases at call sites"

**Mitigation**: Acceptable trade-off for explicitness.

**Before:**
```python
orchestrator = container.upgrade_orchestrator()
```

**After:**
```python
orchestrator = UpgradeOrchestrator(
    screenshot_service=screenshot_service,
    window_interaction_service=window_service,
    cache_service=cache_service,
    network_manager=network_manager,
    detector=detector,
)
```

**Constitutional principle**: Explicit Over Implicit - verbose but clear is better than concise but magical.

#### Risk 2: "Harder to swap implementations"

**Reality**: We're not swapping implementations. These are concrete, single-implementation classes.

**If we DID need polymorphism**, we'd use protocols:
```python
orchestrator: IUpgradeOrchestrator = UpgradeOrchestrator(...)
```

Constructor injection provides same polymorphism without DI container.

#### Risk 3: "Service changes require updating multiple call sites"

**Reality**: Orchestrator has exactly **3 call sites** (CountWorkflow, SpendWorkflow, DebugMonitorWorkflow).

If orchestrator signature changes, we update 3 workflows. This is:
- **Acceptable**: Small number of call sites
- **Good**: Forces explicit review of impact
- **Better than DI**: No hidden coupling through container

---

## Conclusion

Both **ProgressBarMonitor** and **UpgradeOrchestrator** should be **removed from the DI container**.

### Summary of Violations

| Component | YAGNI | Simplicity | Explicit | Reusability | Polymorphism |
|-----------|-------|------------|----------|-------------|--------------|
| **ProgressBarMonitor** | ❌ Factory for one-shot | ❌ Double factory | ❌ Hidden creation | ❌ Only used by orchestrator | ❌ Always concrete |
| **UpgradeOrchestrator** | ❌ Factory for one-shot | ❌ Triple indirection | ❌ Hidden dependencies | ❌ Not shared between workflows | ❌ Always concrete |

### Recommended Architecture

**Container manages infrastructure only:**
- AppData (configuration)
- CacheService (persistence)
- ScreenshotService (platform abstraction)
- WindowInteractionService (platform abstraction)
- LocateRegionService (reusable service)
- NetworkManager (platform abstraction)
- ProgressBarStateDetector (stateless algorithm)

**Application layer constructs coordination:**
- Workflows construct orchestrator
- Orchestrator constructs monitor
- Monitor uses detector (from container)

### Implementation Priority

1. **Phase 1**: Remove workflows from DI (already planned)
2. **Phase 2**: Remove orchestrator from DI (this document)
3. **Phase 3**: Remove monitor from DI (this document)

**Phases 2-3 can be done together** since they're tightly coupled (orchestrator depends on monitor).

### Final Recommendation

**Remove both ProgressBarMonitor and UpgradeOrchestrator from container in same refactoring:**

1. Update container to remove factory providers
2. Update UpgradeOrchestrator to accept detector instead of monitor
3. Update workflows to construct orchestrator directly
4. Update tests to construct orchestrator/monitor with mocked services
5. Verify simpler, clearer dependency graph

**Result**: Container manages only true infrastructure services, application layer explicitly constructs coordination logic.
