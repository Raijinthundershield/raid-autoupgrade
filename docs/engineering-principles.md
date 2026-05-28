# Engineering Principles

Goal: **minimize blast radius**. Every principle serves this goal — when a requirement changes or a bug is fixed, the number of files that must change should be as small as possible.

## DRY (Don't Repeat Yourself)

Every piece of knowledge or logic has a single authoritative location.

- **Do**: Extract shared logic into a single function, class, or constant.
- **Don't**: Copy behavior across modules and let copies drift independently.
- **Signal**: If the same condition, formula, or sequence appears twice, one copy is already wrong.

## Separation of Concerns

Each module or layer owns exactly one kind of responsibility.

- **Do**: Keep detection logic in the detection layer, coordination in the orchestration layer, I/O in services.
- **Don't**: Mix concerns — a detector that also logs, a service that also computes business rules.
- **Signal**: If you cannot summarize a module's responsibility in one sentence, it owns too much.

## Explicit Dependencies

Dependencies are declared at construction time — never discovered, fetched from globals, or resolved inside a function body.

- **Do**: Accept all collaborators via constructor parameters.
- **Don't**: Use global state, service locators, or import-time singletons that callers cannot substitute.
- **Signal**: If you cannot instantiate a class in a test without patching module-level state, dependencies are hidden.

## Orthogonality

Changes in one area should not force changes in another unrelated area.

- **Do**: Design modules so their change axes are independent. Detection algorithm changes should not require touching network management.
- **Don't**: Couple things that change for different reasons.
- **Signal**: If fixing a bug in one domain requires editing a file in a different domain, the design is not orthogonal.

## SOLID

Apply the full SOLID set with emphasis on the three most load-bearing principles:

**Single Responsibility (SRP)**: One reason to change per class. If a class must change for two different kinds of requirement, split it.

**Open/Closed (OCP)**: Extend behavior by adding new implementations (new strategies, new conditions), not by modifying existing ones.

**Dependency Inversion (DIP)**: High-level modules depend on abstractions (protocols, abstract base classes), not concrete implementations. Concrete classes are wired at the composition root — the DI container or entry point — not inside business logic.

- **Don't**: Instantiate collaborators inside business logic. Don't let one service class directly reference another concrete service class.

## Modularity

Prefer many small, focused units over few large ones. Module boundaries should be clear; crossings should be explicit.

- **Do**: Keep modules small enough that their full behavior is readable in one pass.
- **Don't**: Let modules accumulate unrelated helpers because they are convenient neighbors.
- **Signal**: If a module has grown difficult to name, it has grown beyond a single concern.

## Summary

| Principle | Blast-radius question |
|-----------|----------------------|
| DRY | Will changing this logic require touching multiple files? |
| SoC | Does this change force edits to unrelated modules? |
| Explicit deps | Can I test this in isolation without patching global state? |
| Orthogonality | Do unrelated change axes stay independent? |
| SOLID / DIP | Does business logic depend on abstractions or on concrete classes? |
| Modularity | Can a new contributor understand this module without reading its callers? |
