# ============================================================
# EXAMPLE TESTS — READ THESE, THEN WRITE YOUR OWN
# ============================================================
# These two tests are provided as scaffolding to show you:
#   1. How to use the `client` fixture from conftest.py
#   2. Two common patterns: empty-list check and create-then-verify
#
# DO NOT count these toward your required test functions.
# Write your own tests in a separate file, e.g. tests/test_<yourname>.py
# ============================================================


def test_list_books_returns_empty_list_initially(client):
    """Books endpoint returns an empty list when no books have been added.

    This is the simplest possible test — it confirms the endpoint exists,
    responds with HTTP 200, and that the store starts clean for every test
    (thanks to the reset() call in conftest.py).
    """
    response = client.get("/books")
    assert response.status_code == 200
    assert response.get_json() == []


def test_create_book_returns_created_book(client):
    """A book POSTed to /books is returned in the response with correct fields.

    This is the create-then-verify pattern: send a POST, inspect the response
    body, and confirm the data you sent came back correctly. You can extend
    this idea to test GET /books after the POST, or chain multiple requests
    to test more complex workflows (e.g. checkout a book and verify
    available_copies decrements).
    """
    payload = {
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "isbn": "978-0132350884",
        "total_copies": 2,
    }
    response = client.post("/books", json=payload)

    assert response.status_code == 201
    data = response.get_json()
    assert data["title"] == "Clean Code"
    assert data["author"] == "Robert C. Martin"
    assert data["available_copies"] == 2
    assert data["id"] == 1  # first item in a fresh store always gets id=1
