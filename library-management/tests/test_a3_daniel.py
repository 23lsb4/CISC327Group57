from datetime import date, timedelta

import pytest

from app import store

a_book = {"title":"A", "author":"B", "isbn":"100", "total_copies":1}
a_member = {"name":"M", "email":"m@example.com"}

def add_book(client, **override):
    response = client.post("/books", json={**a_book, **override})
    assert response.status_code == 201
    return response.get_json()

def add_member(client, **override):
    response = client.post("/members", json={**a_member, **override})
    assert response.status_code == 201
    return response.get_json()

def get_copies(client, book_id):
    return client.get(f"/books/{book_id}").get_json()["available_copies"]

def ui_checkout(client, book_id, member_id):
    return client.post("/ui/loans", data={"book_id":str(book_id), "member_id":str(member_id)})

def ui_return(client, loan_id):
    return client.post(f"/ui/loans/{loan_id}/return")

##COVERAGE: LOANS PAGE (views.loans_page)

def test_ui_loans_page_empty(client):
    response = client.get("/ui/loans")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "<h1>Loans</h1>" in page
    assert "Check Out a Book" in page
    assert "Return</button>" not in page

def test_ui_loans_page_lists_loans(client):
    book = add_book(client)
    member = add_member(client)
    loan = client.post("/loans", json={"book_id":book["id"], "member_id":member["id"]}).get_json()
    response = client.get("/ui/loans")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert f"<td>{loan['id']}</td>" in page
    assert f"<td>{loan['due_date']}</td>" in page
    assert f'/ui/loans/{loan["id"]}/return' in page

def test_ui_checkout_creates_loan(client):
    book = add_book(client, total_copies=2)
    member = add_member(client)
    response = ui_checkout(client, book["id"], member["id"])
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/ui/loans")
    loans = client.get("/loans").get_json()
    assert len(loans) == 1
    assert loans[0]["book_id"] == book["id"]
    assert loans[0]["member_id"] == member["id"]
    assert loans[0]["due_date"] == (date.today() + timedelta(days=14)).isoformat()
    assert get_copies(client, book["id"]) == 1

def test_ui_checkout_unknown_book_creates_nothing(client):
    book = add_book(client)
    member = add_member(client)
    response = ui_checkout(client, 999, member["id"])
    assert response.status_code == 302
    assert client.get("/loans").get_json() == []
    assert get_copies(client, book["id"]) == 1

@pytest.mark.xfail(reason="Known defect (FR-015): the UI checkout never checks available_copies, so a 1-copy book can be checked out twice and copies go to -1.")
def test_ui_checkout_no_copies_left(client):
    book = add_book(client, total_copies=1)
    first = add_member(client, email="m1@example.com")
    second = add_member(client, email="m2@example.com")
    ui_checkout(client, book["id"], first["id"])
    ui_checkout(client, book["id"], second["id"])
    assert len(client.get("/loans").get_json()) == 1
    assert get_copies(client, book["id"]) == 0

##COVERAGE: RETURN LOAN (views.return_loan_page)

def test_ui_return_loan_marks_returned(client):
    book = add_book(client)
    member = add_member(client)
    ui_checkout(client, book["id"], member["id"])
    assert get_copies(client, book["id"]) == 0
    response = ui_return(client, 1)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/ui/loans")
    loan = client.get("/loans").get_json()[0]
    assert loan["return_date"] == date.today().isoformat()
    assert get_copies(client, book["id"]) == 1
    assert "Return</button>" not in client.get("/ui/loans").get_data(as_text=True)

def test_ui_return_already_returned_loan_no_extra_copy(client):
    book = add_book(client)
    member = add_member(client)
    ui_checkout(client, book["id"], member["id"])
    ui_return(client, 1)
    response = ui_return(client, 1)
    assert response.status_code == 302
    assert get_copies(client, book["id"]) == 1
    assert client.get("/loans").get_json()[0]["return_date"] == date.today().isoformat()

def test_ui_return_missing_loan_changes_nothing(client):
    book = add_book(client)
    member = add_member(client)
    ui_checkout(client, book["id"], member["id"])
    response = ui_return(client, 999)
    assert response.status_code == 302
    assert client.get("/loans").get_json()[0]["return_date"] is None
    assert get_copies(client, book["id"]) == 0

def test_ui_return_loan_after_book_deleted(client):
    book = add_book(client)
    member = add_member(client)
    ui_checkout(client, book["id"], member["id"])
    client.post(f"/ui/books/{book['id']}/delete")
    response = ui_return(client, 1)
    assert response.status_code == 302
    assert store.loans[1].return_date == date.today()
    assert book["id"] not in store.books
