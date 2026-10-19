"""Unit tests for the Notes API. Agents may add tests here, but must never delete or weaken them."""

import pytest
from pydantic import ValidationError

from app.main import NoteIn, NoteStore, normalise_tags


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_note_returns_201_and_assigns_id(client):
    response = client.post("/notes", json={"title": "First", "body": "Hello"})
    assert response.status_code == 201
    assert response.json() == {"id": 1, "title": "First", "body": "Hello", "tags": []}


def test_body_defaults_to_empty_string(client):
    response = client.post("/notes", json={"title": "No body"})
    assert response.status_code == 201
    assert response.json()["body"] == ""


def test_empty_title_is_rejected(client):
    response = client.post("/notes", json={"title": ""})
    assert response.status_code == 422


def test_title_longer_than_100_characters_is_rejected(client):
    response = client.post("/notes", json={"title": "x" * 101})
    assert response.status_code == 422


def test_list_notes_returns_all_notes_in_creation_order(client):
    client.post("/notes", json={"title": "A"})
    client.post("/notes", json={"title": "B"})
    titles = [note["title"] for note in client.get("/notes").json()]
    assert titles == ["A", "B"]


def test_get_unknown_note_returns_404(client):
    assert client.get("/notes/999").status_code == 404


def test_delete_note_then_it_is_gone(client):
    note_id = client.post("/notes", json={"title": "Temp"}).json()["id"]
    assert client.delete(f"/notes/{note_id}").status_code == 204
    assert client.get(f"/notes/{note_id}").status_code == 404


def test_delete_unknown_note_returns_404(client):
    assert client.delete("/notes/999").status_code == 404


def test_store_ids_keep_increasing_after_delete():
    store = NoteStore()
    first = store.create(NoteIn(title="one"))
    store.delete(first.id)
    second = store.create(NoteIn(title="two"))
    assert second.id == first.id + 1


def test_store_clear_resets_ids():
    store = NoteStore()
    store.create(NoteIn(title="one"))
    store.clear()
    assert store.list() == []
    assert store.create(NoteIn(title="again")).id == 1


def test_normalise_tags_trims_lowercases_and_dedupes_in_order():
    assert normalise_tags(["  Work ", "work", "Urgent", "URGENT"]) == ["work", "urgent"]


def test_note_in_defaults_to_no_tags():
    assert NoteIn(title="x").tags == []


def test_note_in_normalises_tags():
    assert NoteIn(title="x", tags=[" A ", "a", "B-1"]).tags == ["a", "b-1"]


@pytest.mark.parametrize("bad", ["", "  ", "x" * 21, "a b", "a_b", "café"])
def test_note_in_rejects_invalid_tag(bad):
    with pytest.raises(ValidationError):
        NoteIn(title="x", tags=[bad])


def test_note_in_rejects_more_than_five_distinct_tags():
    with pytest.raises(ValidationError):
        NoteIn(title="x", tags=list("abcdef"))


def test_store_list_filters_by_normalised_tag():
    store = NoteStore()
    store.create(NoteIn(title="one", tags=["work"]))
    store.create(NoteIn(title="two"))
    assert [n.title for n in store.list(" WORK ")] == ["one"]
    assert store.list("nope") == []
