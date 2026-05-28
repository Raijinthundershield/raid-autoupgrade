# Testing: Practical Conventions

Supplements [testing.md](testing.md) with concrete patterns used in this codebase.

## Stubs over mocks

Use plain stub classes instead of `unittest.mock.MagicMock` or `patch`.

`MagicMock` returns another `MagicMock` for any attribute or call. A test can pass while asserting on the wrong thing — a `MagicMock` where a `bool` was expected, for instance. `patch` targets internal names; if the implementation is refactored the patch breaks even though behavior did not change.

Stubs are explicit about what they simulate and validated by the type checker.

```python
# Good — pyright validates this satisfies WindowInteractionProtocol structurally
class _WindowStub:
    def __init__(self, *, detected: bool) -> None:
        self._detected = detected

    def window_exists(self, window_title: str) -> bool:
        return self._detected


# Bad — MagicMock.window_exists() returns MagicMock, not bool
window_mock = MagicMock()
window_mock.window_exists.return_value = True  # easy to get wrong, nothing validates it
```

## Protocols as the stub spec

This codebase defines `@runtime_checkable` Protocols in `protocols.py`. Every stub must implement the same method signatures as the Protocol for the service it replaces.

The type checker enforces conformance structurally — no explicit inheritance from the Protocol is needed or wanted. If the Protocol grows a method that a route starts calling, the stub will fail to type-check, which is the correct failure signal.

You can also assert conformance at runtime in tests where it matters:

```python
assert isinstance(_WindowStub(detected=True), WindowInteractionProtocol)
```

## Injection points, not internals

Inject stubs at the declared boundary — `app.dependency_overrides` for API routes, constructor arguments for services and orchestrators. Never `patch` an internal import or attribute.

```python
# Good — override at the Depends boundary
app.dependency_overrides[get_window_service] = lambda: _WindowStub(detected=True)

# Bad — patch an internal name
with patch("autoraid.api.routes.status.window_service"):
    ...
```

## Where stubs live

Define stubs at the top of the test file that uses them, prefixed with `_` to mark them as private to that module. Do not share stubs across test files — duplication is fine here; shared stubs create hidden coupling between tests.
