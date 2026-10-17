# 001: Tag notes and filter by tag

Status: pending
Owner: <your name>
Risk: low

## Why

Users with many notes want to group them ("work", "ideas") and see one group at a time.

## What

1. `POST /notes` accepts an optional `tags` field: a list of strings. Every note in every
   response includes `tags` (an empty list when none were given).
2. Tags are normalised before validation and storage: trim surrounding whitespace, convert
   to lowercase, remove duplicates while keeping the order of first appearance.
3. After normalisation, each tag must be 1 to 20 characters long and contain only the
   ASCII characters a-z, 0-9 and "-". A note can have at most 5 tags. Anything else is
   rejected with 422 and nothing is stored. An empty or whitespace-only tag is invalid,
   not silently dropped.
4. `GET /notes?tag=<tag>` returns only notes that have that tag. The query value is
   normalised the same way, so `?tag=Work` matches a note tagged "work". An unknown tag
   returns an empty list. Without `tag`, `GET /notes` behaves exactly as before.

## Acceptance criteria

- AC1: A note created without tags has `"tags": []`.
- AC2: `["  Work ", "work", "Urgent"]` is stored as `["work", "urgent"]`.
- AC3: More than 5 distinct tags after normalisation returns 422. Seven inputs that
  normalise to 5 distinct tags are accepted.
- AC4: Tags that are empty, longer than 20 characters, or contain other characters
  (spaces, underscores, accents, emoji) return 422.
- AC5: `GET /notes?tag=Work` returns exactly the notes tagged "work", in creation order.
- AC6: `GET /notes?tag=unknown` returns `[]`.
- AC7: All spec 000 acceptance tests still pass.

## Out of scope

Renaming or removing tags on existing notes, tag counts, persistence. Do not change
the behaviour or response shape of any other endpoint beyond adding `tags`.

## Notes for the implementer

Keep validation in the pydantic model (a field validator), not in the route handlers.
Add unit tests for the normalisation logic.

## How to finish

Implement until the acceptance tests pass, add unit tests for your code, then change
the line at the top to "Status: implemented" in the same pull request.
