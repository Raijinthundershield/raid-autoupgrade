# TASK

A reviewer flagged **blocking** findings on branch `{{BRANCH}}`. Resolve them.

You did NOT write this code — you are a fresh pair of eyes brought in
specifically to fix the review's blocking findings. Context on what was built is
below.

# WHAT WAS IMPLEMENTED

In-scope issues:

<spec-issues>

{{SPEC_ISSUES}}

</spec-issues>

The implementer left a handoff describing the intent, the public interface, the
key design/test decisions, and anything left out of scope. Read it before
touching anything — it is your fastest path to the original intent:

<implementer-handoff>

{{HANDOFFS}}

</implementer-handoff>

The changes under review are the diff `git diff {{FIXED_POINT}}...HEAD`. Read it.

# BLOCKING FINDINGS TO RESOLVE

These are the only findings you must address (read the full file at
`{{BLOCKING_PATH}}`):

<blocking>

{{BLOCKING_FINDINGS}}

</blocking>

Do not chase findings that are not listed here — judgment calls were
deliberately left for the human and are out of scope for you.

# HARD RULES

- **Fix the production code, or a test that is genuinely wrong.** NEVER delete or
  weaken a test, loosen an assertion, skip a check, or relax the gate just to go
  green. If a finding can only be "fixed" by weakening verification, leave it
  and note why in a `gh issue comment`.
- Stay within the scope of the listed findings. Do not refactor unrelated code.
- Honor `docs/engineering-principles.md` and the testing docs.

# FEEDBACK LOOP (the gate)

Before you are done, the full gate must be green:

1. `uv run pytest`
2. `uv run pre-commit run --all-files`
3. Only if you touched `frontend/`: from `frontend/`, `npm install` then
   `npm run build` and `npm test`.

# COMMIT

Commit with a conventional-commit message (e.g.
`fix(events): address review findings`), body noting it resolves review
findings, and the trailer `Co-Authored-By: Claude <noreply@anthropic.com>`. Use
`git commit -F` for multi-line messages. No `RALPH:` prefix.

When the findings are resolved and the gate is green, output:

<promise>COMPLETE</promise>
