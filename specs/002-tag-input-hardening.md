# 002: Reject ambiguous tag input

Status: pending
Owner: delorenzostefano
Risk: low

## Why

Reviewing spec 001 showed two inputs whose behaviour was never decided: an empty tag
filter, and characters that only become ASCII after lowercasing. Undecided behaviour is
whatever the implementation happens to do; we want it explicit.

## What

1. `GET /notes?tag=<value>`: after normalisation (trim, lowercase), the value must satisfy
   the same rules as a stored tag (1 to 20 characters of a-z, 0-9 and "-"). Otherwise the
   request is rejected with 422. An empty or whitespace-only value is invalid. Without the
   `tag` parameter, `GET /notes` behaves exactly as before.
2. Tags (in `POST /notes` and in the filter) must contain only ASCII characters before
   normalisation. A non-ASCII character is rejected with 422, even if lowercasing would turn
   it into an allowed character (for example the Kelvin sign U+212A).

## Acceptance criteria

- AC1: `GET /notes?tag=` returns 422.
- AC2: `GET /notes?tag=%20%20` (whitespace only) returns 422.
- AC3: `GET /notes?tag=a_b` returns 422.
- AC4: `POST /notes` with the tag "\u212a" (Kelvin sign) returns 422 and stores nothing.
- AC5: `GET /notes?tag=\u212a` returns 422.

## Out of scope

Everything else about tags, including the normalisation rules of spec 001 for valid input.
Do not change any other endpoint.

## Notes for the implementer

Keep validation in pydantic or in one shared function used by both the model and the
filter; don't duplicate the rules. Spec 000 and 001 acceptance tests must keep passing.

## How to finish

Implement until the acceptance tests pass, add unit tests for your code, then change
the line at the top to "Status: implemented" in the same pull request.
