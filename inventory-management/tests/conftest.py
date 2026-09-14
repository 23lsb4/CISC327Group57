import pytest

from app import create_app, store


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    store.reset()
    with app.test_client() as client:
        yield client
    store.reset()
