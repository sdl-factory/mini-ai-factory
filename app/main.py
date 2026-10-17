"""Notes API: the small product that the mini software factory builds and ships.

Deliberately simple, so you can focus on the factory around it rather than the app.
"""

from __future__ import annotations

from itertools import count
from threading import Lock

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, Field

app = FastAPI(title="Notes API", version="0.1.0")


class NoteIn(BaseModel):
    """Payload for creating a note."""

    title: str = Field(min_length=1, max_length=100)
    body: str = Field(default="", max_length=10_000)


class Note(NoteIn):
    """A stored note."""

    id: int


class NoteStore:
    """Thread-safe in-memory store. Data is lost on restart, which is fine for this project."""

    def __init__(self) -> None:
        self._notes: dict[int, Note] = {}
        self._ids = count(1)
        self._lock = Lock()

    def create(self, data: NoteIn) -> Note:
        with self._lock:
            note = Note(id=next(self._ids), **data.model_dump())
            self._notes[note.id] = note
            return note

    def list(self) -> list[Note]:
        with self._lock:
            return list(self._notes.values())

    def get(self, note_id: int) -> Note | None:
        with self._lock:
            return self._notes.get(note_id)

    def delete(self, note_id: int) -> bool:
        with self._lock:
            return self._notes.pop(note_id, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._notes.clear()
            self._ids = count(1)


store = NoteStore()


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness and readiness endpoint. Checks only this process, never dependencies."""
    return {"status": "ok"}


@app.post("/notes", status_code=status.HTTP_201_CREATED)
def create_note(data: NoteIn) -> Note:
    return store.create(data)


@app.get("/notes")
def list_notes() -> list[Note]:
    return store.list()


@app.get("/notes/{note_id}")
def get_note(note_id: int) -> Note:
    note = store.get(note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


@app.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int) -> Response:
    if not store.delete(note_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
