"""Acceptance tests for specs/001-note-tags.md. Owned by humans: agents must not edit this file."""

import pytest

pytestmark = pytest.mark.spec("001")


def create(client, title, tags=None):
    payload = {"title": title}
    if tags is not None:
        payload["tags"] = tags
    return client.post("/notes", json=payload)


def test_ac1_note_without_tags_has_empty_list(client):
    response = create(client, "plain")
    assert response.status_code == 201
    assert response.json()["tags"] == []


def test_ac1_tags_appear_in_list_and_get(client):
    note_id = create(client, "tagged", ["work"]).json()["id"]
    assert client.get(f"/notes/{note_id}").json()["tags"] == ["work"]
    assert client.get("/notes").json()[0]["tags"] == ["work"]


def test_ac2_tags_are_normalised(client):
    response = create(client, "normalise", ["  Work ", "work", "Urgent"])
    assert response.status_code == 201
    assert response.json()["tags"] == ["work", "urgent"]


def test_ac3_more_than_five_distinct_tags_rejected(client):
    response = create(client, "too many", ["a", "b", "c", "d", "e", "f"])
    assert response.status_code == 422
    assert client.get("/notes").json() == []


def test_ac3_duplicates_do_not_count_towards_the_limit(client):
    response = create(client, "dupes", ["a", "A", " a ", "b", "c", "d", "e"])
    assert response.status_code == 201
    assert response.json()["tags"] == ["a", "b", "c", "d", "e"]


@pytest.mark.parametrize(
    "bad_tag",
    ["", "   ", "x" * 21, "has space", "under_score", "café", "emoji\U0001f642"],
)
def test_ac4_invalid_tags_rejected(client, bad_tag):
    assert create(client, "bad", ["ok", bad_tag]).status_code == 422
    assert client.get("/notes").json() == []


def test_ac4_boundary_lengths_accepted(client):
    tags = ["x", "y" * 20, "with-hyphen-2"]
    response = create(client, "edges", tags)
    assert response.status_code == 201
    assert response.json()["tags"] == tags


def test_ac5_filter_by_tag_case_insensitive(client):
    create(client, "first", ["work"])
    create(client, "second", ["home"])
    create(client, "third", ["Work", "urgent"])
    titles = [n["title"] for n in client.get("/notes", params={"tag": "Work"}).json()]
    assert titles == ["first", "third"]


def test_ac6_unknown_tag_returns_empty_list(client):
    create(client, "first", ["work"])
    response = client.get("/notes", params={"tag": "unknown"})
    assert response.status_code == 200
    assert response.json() == []


def test_ac5_no_filter_returns_everything(client):
    create(client, "a", ["work"])
    create(client, "b")
    notes = client.get("/notes").json()
    assert [(n["title"], n["tags"]) for n in notes] == [("a", ["work"]), ("b", [])]
