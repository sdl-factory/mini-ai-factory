# 000: Create, read, list and delete notes

Status: implemented
Owner: <your name>
Risk: low

## Why

Users need a place to store short notes. This is the baseline behaviour every later spec builds on.

## What

A JSON HTTP API with these endpoints:

- `POST /notes` with `{"title": str, "body": str}` creates a note and returns it with an integer `id`.
- `GET /notes` lists all notes in creation order.
- `GET /notes/{id}` returns one note.
- `DELETE /notes/{id}` deletes one note.
- `GET /health` returns `{"status": "ok"}`.

## Acceptance criteria

- AC1: Creating a note returns 201 and the note including a new integer id.
- AC2: `title` is required, 1 to 100 characters; otherwise 422. `body` is optional and defaults to "".
- AC3: Listing returns every note in creation order.
- AC4: Getting or deleting an unknown id returns 404.
- AC5: Deleting a note returns 204, and the note can no longer be fetched.
- AC6: `/health` returns 200 with `{"status": "ok"}`.

## Out of scope

Persistence, authentication, pagination.
