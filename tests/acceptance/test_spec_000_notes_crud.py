"""Acceptance tests for specs/000-notes-crud.md. Owned by humans: agents must not edit this file."""

import pytest

pytestmark = pytest.mark.spec("000")


def test_ac1_create_returns_201_with_id(client):
    response = client.post("/notes", json={"title": "Groceries", "body": "milk"})
    assert response.status_code == 201
    note = response.json()
    assert isinstance(note["id"], int)
    assert note["title"] == "Groceries"
    assert note["body"] == "milk"


@pytest.mark.parametrize("title", ["", "x" * 101])
def test_ac2_invalid_title_is_rejected(client, title):
    assert client.post("/notes", json={"title": title}).status_code == 422


def test_ac2_title_is_required(client):
    assert client.post("/notes", json={"body": "no title"}).status_code == 422


def test_ac2_body_defaults_to_empty(client):
    assert client.post("/notes", json={"title": "t"}).json()["body"] == ""


def test_ac3_list_in_creation_order(client):
    for title in ["one", "two", "three"]:
        client.post("/notes", json={"title": title})
    assert [n["title"] for n in client.get("/notes").json()] == ["one", "two", "three"]


def test_ac4_unknown_id_returns_404(client):
    assert client.get("/notes/12345").status_code == 404
    assert client.delete("/notes/12345").status_code == 404


def test_ac5_delete_then_gone(client):
    note_id = client.post("/notes", json={"title": "bye"}).json()["id"]
    assert client.delete(f"/notes/{note_id}").status_code == 204
    assert client.get(f"/notes/{note_id}").status_code == 404


def test_ac6_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
