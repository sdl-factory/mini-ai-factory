import pytest
from fastapi.testclient import TestClient

from app.main import app, store


@pytest.fixture
def client():
    """A test client with an empty note store, isolated from other tests."""
    store.clear()
    with TestClient(app) as test_client:
        yield test_client
    store.clear()
