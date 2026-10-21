"""Acceptance tests for specs/002-tag-input-hardening.md.

Owned by humans: agents must not edit this file."""

import pytest

pytestmark = pytest.mark.spec("002")

KELVIN = "\u212a"


@pytest.mark.parametrize("value", ["", "  ", "a_b"])
def test_ac1_ac2_ac3_invalid_tag_filter_rejected(client, value):
    assert client.get("/notes", params={"tag": value}).status_code == 422


def test_ac4_non_ascii_tag_rejected_on_create(client):
    response = client.post("/notes", json={"title": "kelvin", "tags": [KELVIN]})
    assert response.status_code == 422
    assert client.get("/notes").json() == []


def test_ac5_non_ascii_tag_filter_rejected(client):
    assert client.get("/notes", params={"tag": KELVIN}).status_code == 422
