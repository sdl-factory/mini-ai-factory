# NNN: Short title

Status: pending
Owner: <human who wrote and approves this spec>
Risk: low | medium | high

## Why

One or two sentences on the user or business need. Agents fill gaps with assumptions,
so explain intent, not just mechanics.

## What

The behaviour to build, precisely. Name endpoints, fields, formats, limits and error cases.

## Acceptance criteria

Each criterion must be testable. A human writes the matching acceptance tests in
tests/acceptance/test_spec_NNN_*.py, marked with @pytest.mark.spec("NNN"), before
any agent starts. Agents never edit those tests.

- AC1: ...
- AC2: ...

## Out of scope

What must NOT change. This stops agents from "helpfully" refactoring unrelated code.

## Notes for the implementer

Constraints, relevant standards, files to look at, things that are easy to get wrong.

## How to finish

Implement until the acceptance tests pass, add unit tests for your code, then change
the line at the top to "Status: implemented" in the same pull request.
