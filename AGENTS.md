# Agent Working Rules

## Complexity vs Impact

- Prefer the simplest implementation that can meet quality goals.
- Do not add substantial code complexity for marginal or unproven quality gains.
- For costly/complex ideas, require measurable expected benefit before implementation.
- Favor low-cost, high-precision heuristics and clear observability over heavy logic.
- For direct, local changes, implement in place and avoid introducing new abstractions/utilities unless there is immediate multi-callsite reuse.

## Quality Gates (Definition of Done)

- All changed code must pass formatting, linting, type checking, and tests before merge.
- Use these baseline commands from repo root:
  - `uv run ruff format .`
  - `uv run ruff check .`
  - `uv run ty check`
  - `uv run pytest`
- Prefer fast, targeted test runs during iteration, then run full test suite before finalizing.
- Do not merge code that disables checks or weakens quality gates without explicit approval.
- Keep lint suppressions as narrow as possible: prefer inline `# noqa` at the exact line, and use per-file ignores only for strong, recurring patterns with explicit justification.

## Coding Standards

- Optimize for readability first: clear names, small functions, explicit control flow, minimal hidden behavior.
- Apply KISS by default; avoid over-engineered abstractions and speculative generalization.
- Apply DRY pragmatically: remove duplication when it improves clarity and maintainability.
- Follow SOLID where it materially improves design, testability, and change safety.
- Keep modules focused with explicit boundaries; avoid tight coupling and cross-module leakage.
- Minimize dependencies and imports; prefer standard library and existing project utilities first.
- Remove dead code, stale flags, and incidental complexity when touching nearby code.
- Do not use default values for environment variables; missing env configuration must fail fast with an explicit error.

## Type Modeling Rules

- Prefer dedicated Pydantic models for complex inputs/outputs over nested or weakly-typed structures.
- Avoid signatures that rely on `dict[str, dict[str, object]]`, `dict[str, Any]`, or similar catch-all typing for domain data.
- If a parameter or return shape has named fields or nested semantics, define a Pydantic model for it.

## Testing and Development Approach

- Prefer TDD for non-trivial logic and regressions: write or update tests before/with implementation changes.
- Every bug fix should include a regression test when feasible.
- Test behavior and contracts, not private implementation details.
- Keep tests deterministic, isolated, and readable.
- Keep automated unit/integration tests under `tests/**`; place environment-dependent/manual checks under `live_tests/**`.
- Do not use `print` in unit/integration tests; `print` is allowed in `live_tests/**` for manual output inspection.

## Docstring Policy

- Add docstrings for every public class, public function, and public method.
- At minimum, document purpose and key inputs/outputs; include `Raises` when exceptions are part of the contract.
- Private helpers (prefixed with `_`) should have docstrings when behavior is non-obvious.

## Documentation Hygiene

- Keep documentation current with code changes in the same branch/PR.
- Update `README.md` for any setup, runtime, config, API, or usage changes.
- Maintain `TODO.md` (if present) by adding/removing items as work is discovered or completed.
- Write every TODO as `what` + `why/so what`; do not include implementation details (`how`).
- Keep focused docs in `docs/*.md` aligned with implementation and examples.
- Prefer small, frequent doc updates over large delayed rewrites.

## Scratchpad Workflow (Mandatory)

- Always use `SCRATCHPAD.md` as the working memory for the current session.
- Put short-lived notes there: temporary tasks, investigation breadcrumbs, follow-ups, and reminders.
- Keep `TODO.md` for long-lived backlog items only; do not use it for session-only notes.
- When a scratchpad item becomes durable, promote it to `TODO.md` and remove it from `SCRATCHPAD.md`.
- Before finalizing a task/PR, clean `SCRATCHPAD.md` by removing completed or stale notes.
