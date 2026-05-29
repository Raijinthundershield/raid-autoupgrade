# Testing

## Philosophy

Test the **contract at each layer seam**, not the implementation inside a layer.

A seam is the boundary between two components — the interface one component exposes to its caller. A contract test asks: "Given these inputs at this boundary, does the component honour its promise?" It does not ask how the component achieves that promise internally.

## What is a contract?

A contract is the observable agreement at a seam:

- **Inputs**: the arguments a component accepts
- **Outputs**: the return value or raised exception
- **Side effects visible to the caller**: state changes on collaborators the caller provided

Anything else — internal state, private methods, intermediate steps, the order in which private helpers are called — is not part of the contract and must not be asserted on.

## How to write a contract test

1. **Identify the seam.** What is the boundary being tested? Name the caller and the callee.
2. **Isolate with mocks at the seam.** Replace every collaborator the callee accepts as a dependency with a test double. Do not patch internals.
3. **Assert on the contract.** Assert on return values, raised exceptions, and calls made to injected collaborators — nothing else.
4. **One scenario per test.** Each test exercises one behavior of the contract: happy path, one error branch, or one edge case.

## Anti-patterns

**Testing internal state**
Asserting on private attributes, intermediate variables, or the internal sequence of steps inside a component. If the implementation is refactored without changing behavior, these tests break unnecessarily.

**Testing implementation details**
Coupling tests to the names of internal methods or the exact call order of private helpers. Tests must survive any refactor that keeps the contract intact.

**Trivial coverage padding**
Tests that assert something which cannot plausibly be wrong — a constructor stored a value, a constant equals itself — written only to hit a coverage number. These add noise without catching regressions.

## Test layers

| Layer | What to test | What to mock |
|-------|-------------|-------------|
| Detection | State classification from image inputs | Nothing — pure function, use fixture images |
| Orchestration | Stop condition logic, monitor state transitions | Detector, services |
| Workflow | Validation rules, stop condition assembly | Orchestrator |
| Service | Service behavior given its platform dependencies | Platform calls (WMI, Win32, diskcache) |
| Job registry | Single-active-job lifecycle and event-queue ordering | `run_fn` (pass a stub that pushes events directly) |
| Settings service | Round-trip persistence of `selected_adapters` and `last_count_result` | `diskcache.Cache` (stub with a plain dict) |
| API routes | Request → status code, response body, dispatched collaborator | Collaborators, via `app.dependency_overrides` |
| WebSocket | Typed job events arrive in order over the stream; stream closes after `done` | `JobRegistry.get_queue` — seed a `queue.Queue` with pre-built events |
| Integration | Workflow → Orchestrator contract end-to-end | Platform services only |
| Frontend reducer | `useJobStream` derived view state from a WS event sequence | Nothing — pure reducer |
| Frontend coordinate math | `displayRectToImageRect` maps display-pixel rects to image-pixel rects across render scales | Nothing — pure function |
| Frontend panel | Panel calls the right endpoint on interaction; renders loading and error states | The HTTP API / WebSocket boundary |
| Regions route | `GET /api/screenshot` → PNG bytes; `PUT /api/regions` → `cache_service.set_regions` called with correct window size | `screenshot_service`, `window_service`, `cache_service` via `app.dependency_overrides` |

Substitute each dependency at its injection point — `app.dependency_overrides` for routes, constructor args elsewhere — never patch internals.

## Frontend testing

The contract philosophy carries across the language boundary unchanged; only the location of the seam differs. On the client the seam is the **network boundary** — a component's collaborators are the HTTP API and the job WebSocket. Mock at that boundary and assert on what the user sees: rendered output and which endpoint was called, never component state, hook internals, or the query cache. The frontend layers are in the table above.

No end-to-end tests for now: the platform (real Raid window, WMI) cannot run headless, so e2e coverage is inherently limited and low-ROI.

## Coverage

Coverage is a signal, not a target. A test suite that fully exercises every contract at every seam will naturally achieve high coverage. Do not add tests to raise a number; add tests to cover a contract that is not yet tested.
