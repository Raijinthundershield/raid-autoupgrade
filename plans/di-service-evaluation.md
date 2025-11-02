# Dependency Injection Service Evaluation

## Executive Summary

This document evaluates all components in the AutoRaid DI container against constitutional principles (YAGNI, Orthogonality, Simplicity Over Complexity, Explicit Over Implicit) to determine which should remain injected.

**Key Findings:**
- ✅ **7 services correctly injected**: AppData, CacheService, ScreenshotService, WindowInteractionService, LocateRegionService, NetworkManager, ProgressBarStateDetector
- ❌ **2 services should NOT be injected**: ProgressBarMonitor (Factory), UpgradeOrchestrator (Factory)
- ❌ **3 workflows should NOT be injected**: CountWorkflow, SpendWorkflow, DebugMonitorWorkflow

**Recommended Container Simplification:**
- **Before**: 13 providers (8 singletons, 5 factories)
- **After**: 8 providers (8 singletons, 0 factories)
- **Impact**: 62% reduction in factory complexity, clearer dependency graph

> **See detailed analysis**: `monitor-orchestrator-injection-analysis.md` for in-depth reasoning on ProgressBarMonitor and UpgradeOrchestrator removal.

---

## Evaluation Criteria

Each component is evaluated on:

1. **Lifecycle**: Singleton (shared) vs. Factory (per-request) vs. One-shot (per-action)
2. **Reusability**: Used by multiple callers vs. single-use
3. **Polymorphism**: Can be swapped/mocked vs. always concrete
4. **Parameters**: Dependencies only vs. mixed with runtime config
5. **Domain Role**: Infrastructure/service layer vs. application/use-case layer

**Decision Matrix:**
- **SHOULD inject**: Shared state, reusable, polymorphic, dependencies only, infrastructure layer
- **SHOULD NOT inject**: One-shot, single-use, always concrete, mixed parameters, application layer

---

## Service-by-Service Evaluation

### ✅ **AppData** (Singleton) - CORRECTLY INJECTED

**Current Usage:**
```python
app_data = providers.Singleton(
    AppData,
    cache_dir=config.cache_dir,
    debug_enabled=config.debug,
)
```

**Evaluation:**
| Criterion | Assessment | Justification |
|-----------|------------|---------------|
| Lifecycle | Singleton | Configuration object, shared across app |
| Reusability | High | Used by CLI, GUI, workflows, services |
| Polymorphism | Low | Always concrete AppData, but mockable for tests |
| Parameters | Config only | Only configuration (cache_dir, debug_enabled) |
| Domain Role | Infrastructure | Application-wide configuration |

**Verdict: ✅ SHOULD INJECT**
- Centralized configuration (DRY principle)
- Shared across all modules (need consistent cache_dir/debug_dir)
- Pure configuration, no external dependencies
- Makes configuration explicit and testable

**Constitutional Alignment:**
- ✅ **Separation of Concerns**: Configuration in one place
- ✅ **Explicit Over Implicit**: All paths derived from single config
- ✅ **DRY**: Single source of truth for directories

---

### ✅ **CacheService** (Singleton) - CORRECTLY INJECTED

**Current Usage:**
```python
cache_service = providers.Singleton(
    CacheService,
    cache=disk_cache,
)
```

**Evaluation:**
| Criterion | Assessment | Justification |
|-----------|------------|---------------|
| Lifecycle | Singleton | Shared cache, needs consistency |
| Reusability | High | Used by workflows, orchestrator, region service |
| Polymorphism | Medium | Can mock disk_cache for tests |
| Parameters | Dependency only | Only depends on disk_cache |
| Domain Role | Infrastructure | Data persistence layer |

**Verdict: ✅ SHOULD INJECT**
- Wraps external library (diskcache)
- Shared state (cache) needs singleton behavior
- Used by multiple services (LocateRegionService, workflows, orchestrator)
- Testable via mock cache

**Constitutional Alignment:**
- ✅ **Orthogonality**: Decouples services from cache implementation
- ✅ **Separation of Concerns**: Persistence abstracted from business logic

---

### ✅ **WindowInteractionService** (Singleton) - CORRECTLY INJECTED

**Current Usage:**
```python
window_interaction_service = providers.Singleton(
    WindowInteractionService,
)
```

**Evaluation:**
| Criterion | Assessment | Justification |
|-----------|------------|---------------|
| Lifecycle | Singleton | Stateless, can be shared |
| Reusability | High | Used by ScreenshotService, workflows, orchestrator |
| Polymorphism | High | ⚠️ Should use protocol abstraction (future work) |
| Parameters | Config only | `use_minimize_trick` (currently hardcoded) |
| Domain Role | Infrastructure | Platform abstraction layer |

**Verdict: ✅ SHOULD INJECT (with future improvement)**
- Wraps platform-specific libraries (pyautogui, pygetwindow)
- Used by multiple services
- **Current issue**: Directly imports pyautogui/pygetwindow (violates Orthogonality)
- **Future work**: Introduce IWindowSystem protocol abstraction

**Constitutional Alignment:**
- ⚠️ **Orthogonality VIOLATION**: Hard dependency on pyautogui/pygetwindow
- ✅ **Separation of Concerns**: Window operations abstracted
- 🔧 **Recommended**: Protocol-based abstraction (separate refactoring)

---

### ✅ **ScreenshotService** (Singleton) - CORRECTLY INJECTED

**Current Usage:**
```python
screenshot_service = providers.Singleton(
    ScreenshotService,
    window_interaction_service=window_interaction_service,
)
```

**Evaluation:**
| Criterion | Assessment | Justification |
|-----------|------------|---------------|
| Lifecycle | Singleton | Stateless, composable |
| Reusability | High | Used by LocateRegionService, orchestrator, CLI, GUI |
| Polymorphism | High | ⚠️ Should use protocol abstraction (future work) |
| Parameters | Dependency only | Only depends on window_interaction_service |
| Domain Role | Infrastructure | Screenshot capture abstraction |

**Verdict: ✅ SHOULD INJECT (with future improvement)**
- Composes WindowInteractionService
- Used across CLI, GUI, workflows
- **Current issue**: Directly imports pyautogui/pygetwindow (same as WindowInteractionService)
- **Future work**: Use IWindowSystem protocol

**Constitutional Alignment:**
- ⚠️ **Orthogonality VIOLATION**: Hard dependency on pyautogui/pygetwindow
- ✅ **Separation of Concerns**: Screenshot logic abstracted
- 🔧 **Recommended**: Protocol-based abstraction (separate refactoring)

---

### ✅ **LocateRegionService** (Singleton) - CORRECTLY INJECTED

**Current Usage:**
```python
locate_region_service = providers.Singleton(
    LocateRegionService,
    cache_service=cache_service,
    screenshot_service=screenshot_service,
)
```

**Evaluation:**
| Criterion | Assessment | Justification |
|-----------|------------|---------------|
| Lifecycle | Singleton | Stateless coordination logic |
| Reusability | High | Used by CLI region commands, GUI region panel |
| Polymorphism | Medium | Composes injected services |
| Parameters | Dependencies only | Only cache_service and screenshot_service |
| Domain Role | Infrastructure | Region detection coordination |

**Verdict: ✅ SHOULD INJECT**
- Coordinates complex region detection logic
- Used by both CLI and GUI
- Composes multiple services (cache, screenshot)
- Business logic worth abstracting into service

**Constitutional Alignment:**
- ✅ **Separation of Concerns**: Region detection isolated
- ✅ **Orthogonality**: Testable via mocked dependencies
- ✅ **DRY**: Region detection in one place

---

### ✅ **NetworkManager** (Singleton) - CORRECTLY INJECTED

**Current Usage:**
```python
network_manager = providers.Singleton(
    NetworkManager,
)
```

**Evaluation:**
| Criterion | Assessment | Justification |
|-----------|------------|---------------|
| Lifecycle | Singleton | Thread-local WMI wrapper |
| Reusability | High | Used by workflows, network CLI/GUI, NetworkContext |
| Polymorphism | Medium | Platform-specific (Windows WMI) |
| Parameters | None | No constructor dependencies |
| Domain Role | Infrastructure | Platform abstraction for network control |

**Verdict: ✅ SHOULD INJECT**
- Wraps platform-specific WMI interface
- Thread-local state management
- Used by workflows and NetworkContext
- Critical for airplane mode trick

**Constitutional Alignment:**
- ✅ **Separation of Concerns**: Network control abstracted
- ⚠️ **Orthogonality**: Tightly coupled to WMI (acceptable for Windows-only tool)
- ✅ **Explicit Over Implicit**: Clear abstraction over WMI complexity

---

### ✅ **ProgressBarStateDetector** (Singleton) - CORRECTLY INJECTED

**Current Usage:**
```python
progress_bar_detector = providers.Singleton(
    ProgressBarStateDetector,
)
```

**Evaluation:**
| Criterion | Assessment | Justification |
|-----------|------------|---------------|
| Lifecycle | Singleton | Pure stateless algorithm |
| Reusability | High | Used by ProgressBarMonitor (Factory) |
| Polymorphism | High | Easily mockable for monitor tests |
| Parameters | None | Stateless CV algorithm |
| Domain Role | Core Logic | Computer vision algorithm |

**Verdict: ✅ SHOULD INJECT**
- Stateless pure function (detect_state method)
- Shared by all monitor instances (no need to recreate)
- Easily testable with fixture images
- Injected into ProgressBarMonitor for mocking

**Constitutional Alignment:**
- ✅ **Orthogonality**: Pure function, no side effects
- ✅ **Separation of Concerns**: Detection logic isolated from monitoring
- ✅ **Testability**: Can test with fixture images

---

### ❌ **ProgressBarMonitor** (Factory) - SHOULD NOT INJECT

**Current Usage:**
```python
progress_bar_monitor = providers.Factory(
    ProgressBarMonitor,
    detector=progress_bar_detector,
)
```

**Evaluation:**
| Criterion | Assessment | Justification |
|-----------|------------|---------------|
| Lifecycle | One-shot | Created once per orchestrator, used for single session |
| Reusability | None | Only used by UpgradeOrchestrator, never shared |
| Polymorphism | None | Always concrete ProgressBarMonitor |
| Parameters | Dependency only | Only depends on detector (singleton) |
| Domain Role | Application Logic | Stateful helper for orchestrator |

**Verdict: ❌ SHOULD NOT INJECT**

**Why REMOVE:**
1. **One-shot usage**: Created once per orchestrator, used for exactly one `run_upgrade_session()`, then discarded
2. **Double factory pattern**: Orchestrator already a factory, monitor factory is redundant
3. **Zero reusability**: Only used by UpgradeOrchestrator, never shared between contexts
4. **Hidden creation**: Users don't see monitor being created
5. **Testing unchanged**: Tests already mock dependencies - just at detector level instead of monitor level
6. **Application layer**: Helper object for orchestrator, not infrastructure service

**Current Pattern (complex):**
```python
# Orchestrator receives monitor via injection
class UpgradeOrchestrator:
    def __init__(self, ..., monitor: ProgressBarMonitor):
        self._monitor = monitor

    def run_upgrade_session(self, session):
        # Monitor already created, reused for this session
        current_state = self._monitor.process_frame(roi)
```

**Proposed Pattern (simple):**
```python
# Orchestrator creates monitor per session
class UpgradeOrchestrator:
    def __init__(self, ..., detector: ProgressBarStateDetector):
        self._detector = detector

    def run_upgrade_session(self, session):
        monitor = ProgressBarMonitor(self._detector)  # Fresh per session
        current_state = monitor.process_frame(roi)
```

**Benefits of removal:**
- ✅ Simpler container (one fewer factory)
- ✅ Explicit monitor lifecycle (created when needed, not upfront)
- ✅ Clearer ownership (orchestrator owns monitor creation)
- ✅ Testing improved (test real monitor with mocked detector)

**Constitutional Violations:**
- ❌ **YAGNI**: Factory pattern provides no benefit (monitor = 1:1 with session)
- ❌ **Simplicity**: Double factory (orchestrator factory creates monitor factory)
- ❌ **Explicit Over Implicit**: Monitor creation hidden in container

> **See detailed analysis**: `monitor-orchestrator-injection-analysis.md` Part 1 for complete reasoning

---

### ❌ **UpgradeOrchestrator** (Factory) - SHOULD NOT INJECT

**Current Usage:**
```python
upgrade_orchestrator = providers.Factory(
    UpgradeOrchestrator,
    screenshot_service=screenshot_service,
    window_interaction_service=window_interaction_service,
    cache_service=cache_service,
    network_manager=network_manager,
    monitor=progress_bar_monitor,  # Also a factory!
)
```

**Evaluation:**
| Criterion | Assessment | Justification |
|-----------|------------|---------------|
| Lifecycle | One-shot | Created per workflow, lifetime = workflow lifetime |
| Reusability | None | Each workflow gets its own orchestrator, never shared |
| Polymorphism | None | Always concrete UpgradeOrchestrator |
| Parameters | Dependencies only | All injected services |
| Domain Role | **Application Layer** | Coordination logic (knows about "upgrade sessions") |

**Verdict: ❌ SHOULD NOT INJECT**

**Why REMOVE:**
1. **Effectively one-shot**: Created per workflow, lifetime = workflow lifetime, never shared between workflows
2. **Triple indirection**: Workflow → Orchestrator (factory) → Monitor (factory) → Detector (singleton)
3. **Application layer**: Coordination logic, not infrastructure (knows about "upgrade sessions", not reusable context-free service)
4. **Not truly shared**: Each workflow gets its own orchestrator instance (CountWorkflow gets one, SpendWorkflow gets one, etc.)
5. **Hidden dependencies**: 5 service dependencies invisible at call site
6. **Testing improved**: Test real orchestrator with mocked services instead of mocking orchestrator itself

**Current Pattern (complex):**
```python
# Workflow receives orchestrator from factory (after workflows removed from DI)
@inject
def count(
    orchestrator_factory: Callable = Provide[Container.upgrade_orchestrator.provider],
    ...
):
    orchestrator = orchestrator_factory()  # Hidden dependency graph
    workflow = CountWorkflow(orchestrator=orchestrator, ...)
```

**Proposed Pattern (simple):**
```python
# Workflow constructs orchestrator explicitly
@inject
def count(
    screenshot_service: ScreenshotService = Provide[Container.screenshot_service],
    window_service: WindowInteractionService = Provide[Container.window_interaction_service],
    cache_service: CacheService = Provide[Container.cache_service],
    network_manager: NetworkManager = Provide[Container.network_manager],
    detector: ProgressBarStateDetector = Provide[Container.progress_bar_detector],
):
    orchestrator = UpgradeOrchestrator(
        screenshot_service=screenshot_service,
        window_interaction_service=window_service,
        cache_service=cache_service,
        network_manager=network_manager,
        detector=detector,  # Orchestrator creates monitor internally
    )
    workflow = CountWorkflow(
        orchestrator=orchestrator,
        cache_service=cache_service,
        window_interaction_service=window_service,
        network_manager=network_manager,
        network_adapter_ids=adapter_ids,
        max_attempts=99,
    )
```

**Benefits of removal:**
- ✅ Simpler container (one fewer factory, 62% reduction when combined with workflow/monitor removal)
- ✅ Explicit dependency graph (all 5 dependencies visible at construction)
- ✅ Clearer ownership (workflow owns orchestrator creation)
- ✅ Testing improved (test real orchestrator with mocked services, better coverage)

**Key Insight - Not Truly Shared:**
- Unlike CacheService (shared by ALL workflows/services), orchestrator is **NOT shared**
- Each workflow creates its own orchestrator instance
- Orchestrator lifetime = workflow lifetime (created together, destroyed together)
- Factory pattern suggests reusability that doesn't exist

**Constitutional Violations:**
- ❌ **YAGNI**: Factory pattern for 1:1 lifecycle objects
- ❌ **Simplicity**: Triple indirection (workflow → orchestrator factory → monitor factory → detector)
- ❌ **Explicit Over Implicit**: 5 hidden dependencies in container
- ❌ **Application Layer in DI**: Orchestrator is coordination logic, not infrastructure

> **See detailed analysis**: `monitor-orchestrator-injection-analysis.md` Part 2 for complete reasoning

---

### ❌ **CountWorkflow** (Factory) - SHOULD NOT INJECT

**Current Usage:**
```python
count_workflow_factory = providers.Factory(
    CountWorkflow,
    cache_service=cache_service,
    window_interaction_service=window_interaction_service,
    network_manager=network_manager,
    orchestrator=upgrade_orchestrator,  # Missing runtime params!
)
```

**Evaluation:**
| Criterion | Assessment | Justification |
|-----------|------------|---------------|
| Lifecycle | One-shot | Created per user action, used once, discarded |
| Reusability | None | Single-use per CLI/GUI invocation |
| Polymorphism | None | Always concrete CountWorkflow |
| Parameters | **Mixed** | Dependencies + runtime config (network_adapter_ids, max_attempts, debug_dir) |
| Domain Role | **Application Layer** | Use-case orchestration |

**Verdict: ❌ SHOULD NOT INJECT**

**Why REMOVE:**
1. **YAGNI Violation**: Factory pattern adds no value for one-shot objects
2. **Mixed Parameters**: Runtime config (network_adapter_ids, max_attempts) not in factory
3. **Application Layer**: Workflows are use-cases, not infrastructure
4. **Zero Polymorphism**: Will never swap CountWorkflow for alternative implementation
5. **Already Testable**: Tests construct directly with mocked services

**Current Pattern (complex):**
```python
@inject
def count(
    count_workflow_factory: Callable = Provide[Container.count_workflow_factory.provider],
):
    ctx = click.get_current_context()
    app_data = ctx.obj["app_data"]

    workflow = count_workflow_factory(  # Factory call
        network_adapter_ids=list(network_adapter_id),  # Runtime param
        max_attempts=99,  # Runtime param
        debug_dir=app_data.debug_dir,  # Runtime param
    )
```

**Proposed Pattern (simple):**
```python
@inject
def count(
    cache_service: CacheService = Provide[Container.cache_service],
    window_service: WindowInteractionService = Provide[...],
    network_manager: NetworkManager = Provide[...],
    orchestrator_factory: Callable = Provide[Container.upgrade_orchestrator.provider],
    app_data: AppData = Provide[Container.app_data],
):
    workflow = CountWorkflow(  # Direct construction
        cache_service=cache_service,
        window_interaction_service=window_service,
        network_manager=network_manager,
        orchestrator=orchestrator_factory(),
        network_adapter_ids=list(network_adapter_id),
        max_attempts=99,
        debug_dir=app_data.debug_dir,
    )
```

**Constitutional Violations:**
- ❌ **YAGNI**: Factory pattern provides no benefit
- ❌ **Simplicity Over Complexity**: Factory indirection is unnecessary
- ❌ **Explicit Over Implicit**: Runtime params hidden in factory call

---

### ❌ **SpendWorkflow** (Factory) - SHOULD NOT INJECT

**Same analysis as CountWorkflow** - all arguments apply identically.

**Additional runtime parameters:**
- `max_upgrade_attempts`: User-specified limit
- `continue_upgrade`: Boolean flag for level 10+ artifacts

**Verdict: ❌ SHOULD NOT INJECT** (same reasoning as CountWorkflow)

---

### ❌ **DebugMonitorWorkflow** (Factory) - SHOULD NOT INJECT

**Same analysis as CountWorkflow** - all arguments apply identically.

**Additional runtime parameters:**
- `max_frames`: Debug frame capture limit
- `debug_dir`: Required for debug output

**Verdict: ❌ SHOULD NOT INJECT** (same reasoning as CountWorkflow)

---

## Summary Matrix

| Component | Type | Lifecycle | Inject? | Reason |
|-----------|------|-----------|---------|--------|
| **AppData** | Config | Singleton | ✅ YES | Shared configuration, used everywhere |
| **disk_cache** | External | Singleton | ✅ YES | External library wrapper |
| **CacheService** | Service | Singleton | ✅ YES | Shared cache state, abstraction layer |
| **WindowInteractionService** | Service | Singleton | ✅ YES | Platform abstraction, reusable (⚠️ needs protocol) |
| **ScreenshotService** | Service | Singleton | ✅ YES | Reusable screenshot logic (⚠️ needs protocol) |
| **LocateRegionService** | Service | Singleton | ✅ YES | Complex coordination logic |
| **NetworkManager** | Service | Singleton | ✅ YES | Platform abstraction (WMI) |
| **ProgressBarStateDetector** | Core | Singleton | ✅ YES | Stateless algorithm, shared |
| **ProgressBarMonitor** | Core | Factory | ❌ NO | One-shot per session, helper object |
| **UpgradeOrchestrator** | Service | Factory | ❌ NO | One-shot per workflow, app layer |
| **CountWorkflow** | Workflow | Factory | ❌ NO | One-shot, mixed params, app layer |
| **SpendWorkflow** | Workflow | Factory | ❌ NO | One-shot, mixed params, app layer |
| **DebugMonitorWorkflow** | Workflow | Factory | ❌ NO | One-shot, mixed params, app layer |

---

## Recommendations

### Phase 1: Remove Workflows from DI (High Priority) ❌

**Action**: Remove all 3 workflow factory providers from container
- Remove `CountWorkflow`, `SpendWorkflow`, `DebugMonitorWorkflow` factory providers
- Update CLI/GUI to construct workflows directly with injected services
- Update tests to match new construction pattern

**Resources**:
- **Plan**: `plans/remove-workflow-injection-plan.md`
- **Tasklist**: `plans/remove-workflow-injection-tasklist.md`
- **Estimated Time**: ~4 hours

**Impact**:
- Container: 13 → 10 providers (23% reduction in factory complexity)
- Simpler CLI/GUI injection signatures (services only, not workflow factories)
- Explicit runtime parameters at call site

---

### Phase 2: Remove Orchestrator & Monitor from DI (High Priority) ❌

**Action**: Remove orchestrator and monitor factory providers from container
- Remove `UpgradeOrchestrator` factory provider
- Remove `ProgressBarMonitor` factory provider
- Update `UpgradeOrchestrator` to accept `detector` instead of `monitor`
- Update workflows to construct orchestrator directly
- Update tests to construct orchestrator/monitor with mocked services

**Resources**:
- **Analysis**: `plans/monitor-orchestrator-injection-analysis.md` (detailed reasoning)

**Impact**:
- Container: 10 → 8 providers (62% total reduction in factory complexity from baseline)
- Zero factories in container (only singletons for infrastructure)
- Explicit dependency graph: Workflow → Orchestrator → Monitor → Detector
- Testing improved: test real orchestrator/monitor with mocked services

**Why together?**:
- Orchestrator depends on monitor (tightly coupled)
- Both violate same principles (one-shot, application layer)
- Refactoring together avoids intermediate state

---

### Phase 3: Protocol-Based Window Abstraction (Medium Priority) ⚠️

**Action**: Introduce protocol abstraction for platform dependencies
- Create `IWindowSystem` protocol
- Implement `PyAutoGUIWindowSystem` adapter
- Inject protocol instead of concrete WindowInteractionService/ScreenshotService
- Enables full testability without GUI dependencies

**Benefits**:
- Can run tests in CI/CD without X11/Windows
- Fixes Orthogonality violations (hard dependencies on pyautogui/pygetwindow)
- Maintains same DI pattern (protocol injection)

**Constitutional Principle**: Orthogonality (decouple from platform)

---

### Phase 4: Expose Configuration (Low Priority) ⚠️

**Action**: Make hidden configuration explicit
- Add `use_minimize_trick` to container config
- Allow users to control window activation behavior

**Constitutional Principle**: Explicit Over Implicit

---

## Constitutional Alignment Summary

### Services That Follow Principles ✅

**Infrastructure Services (Keep in DI):**
- **AppData, CacheService, LocateRegionService**: Perfect examples of Separation of Concerns
- **NetworkManager**: Good platform abstraction (Explicit Over Implicit)
- **ProgressBarStateDetector**: Excellent Orthogonality (pure stateless function)
- **WindowInteractionService, ScreenshotService**: Good abstraction despite needing protocol improvement

These services are **context-free, reusable infrastructure** that should remain in DI container.

### Services That Violate Principles ❌

**Application Logic (Remove from DI):**
- **Workflows (CountWorkflow, SpendWorkflow, DebugMonitorWorkflow)**:
  - ❌ YAGNI: Factory pattern for one-shot objects
  - ❌ Simplicity: Unnecessary indirection
  - ❌ Mixed Parameters: Dependencies + runtime config anti-pattern
  - ❌ Application Layer: Use-case orchestration, not infrastructure

- **UpgradeOrchestrator**:
  - ❌ YAGNI: Factory for 1:1 lifecycle with workflow
  - ❌ Simplicity: Triple indirection (workflow → orchestrator → monitor)
  - ❌ Application Layer: Knows about "upgrade sessions" (context-aware)
  - ❌ Not Shared: Each workflow creates its own instance

- **ProgressBarMonitor**:
  - ❌ YAGNI: Factory for one-shot per session
  - ❌ Simplicity: Double factory (orchestrator → monitor)
  - ❌ Application Layer: Helper object for orchestrator, not infrastructure

These components are **context-aware application logic** that should be constructed directly.

### Services Needing Improvement ⚠️

- **WindowInteractionService/ScreenshotService**: Orthogonality violations (hard dependencies on pyautogui/pygetwindow)
  - **Fix**: Protocol-based abstraction (Phase 3)

---

## Conclusion

After deeper analysis, the AutoRaid DI container has **5 components that should be removed** (workflows + orchestrator + monitor), not just workflows.

**Key Insight**: DI containers should manage **infrastructure only**, not **application logic**.

| Layer | What It Is | DI Container? | Examples |
|-------|------------|---------------|----------|
| **Infrastructure** | Context-free, reusable services | ✅ YES | CacheService, NetworkManager, ScreenshotService |
| **Application** | Context-aware coordination logic | ❌ NO | Workflows, Orchestrator, Monitor |

**Refactoring Priority:**
1. **Phase 1**: Remove workflows (already planned, ~4 hours)
2. **Phase 2**: Remove orchestrator & monitor (recommended together, tightly coupled)
3. **Phase 3**: Protocol abstraction for window services (future improvement)

**Final Container State:**
- **Before**: 13 providers (8 singletons, 5 factories)
- **After Phases 1-2**: 8 providers (8 singletons, 0 factories)
- **Result**: Simpler, clearer, constitutionally aligned architecture

The architecture will be **fundamentally sound** with container managing only true infrastructure services and application layer explicitly constructing coordination logic.
