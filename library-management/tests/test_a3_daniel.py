from datetime import date, timedelta

from unittest.mock import patch

import pytest

import notification_service
from app import store
from app.models.loan import Loan

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

def add_loan_to_store(loan_id, book_id, member_id, due_date, return_date=None):
    store.loans[loan_id] = Loan(id=loan_id, book_id=book_id, member_id=member_id,
                                due_date=due_date, return_date=return_date)

def get_loan(client, book_id):
    return client.get(f"/loans?book_id={book_id}").get_json()[0]

##FEATURE: OVERDUE REMINDER NOTIFICATION (failure and non-trigger paths)

def test_reminder_failure_reports_not_sent(client, monkeypatch):
    monkeypatch.setattr("app.routes.loans.send_notification",
                        lambda recipient, subject, message: False)
    book = add_book(client)
    member = add_member(client)
    add_loan_to_store(80, book["id"], member["id"], date.today() - timedelta(days=3))
    response = client.post("/loans/80/remind")
    assert response.status_code == 200
    data = response.get_json()
    assert data["notification_sent"] is False
    assert data["reminded"] is False
    saved_loan = get_loan(client, book["id"])
    assert saved_loan["reminded"] is False
    assert saved_loan["overdue"] is True
    assert saved_loan["return_date"] is None

def test_reminder_failure_can_be_retried(client, monkeypatch):
    book = add_book(client)
    member = add_member(client)
    add_loan_to_store(81, book["id"], member["id"], date.today() - timedelta(days=5))
    monkeypatch.setattr("app.routes.loans.send_notification",
                        lambda recipient, subject, message: False)
    first = client.post("/loans/81/remind")
    assert first.status_code == 200
    assert first.get_json()["notification_sent"] is False
    assert get_loan(client, book["id"])["reminded"] is False
    monkeypatch.setattr("app.routes.loans.send_notification",
                        lambda recipient, subject, message: True)
    second = client.post("/loans/81/remind")
    assert second.status_code == 200
    assert second.get_json()["notification_sent"] is True
    assert get_loan(client, book["id"])["reminded"] is True

def test_no_reminder_for_loan_not_overdue(client):
    book = add_book(client)
    member = add_member(client)
    add_loan_to_store(82, book["id"], member["id"], date.today() + timedelta(days=3))
    with patch("app.routes.loans.send_notification") as mock_send:
        response = client.post("/loans/82/remind")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Loan is not overdue"}
    assert get_loan(client, book["id"])["reminded"] is False
    mock_send.assert_not_called()

def test_no_reminder_on_due_date_boundary(client):
    book = add_book(client)
    member = add_member(client)
    add_loan_to_store(83, book["id"], member["id"], date.today())
    with patch("app.routes.loans.send_notification") as mock_send:
        response = client.post("/loans/83/remind")
    assert response.status_code == 400
    saved_loan = get_loan(client, book["id"])
    assert saved_loan["overdue"] is False
    assert saved_loan["reminded"] is False
    mock_send.assert_not_called()

def test_no_reminder_for_returned_loan(client):
    book = add_book(client)
    member = add_member(client)
    add_loan_to_store(84, book["id"], member["id"], date.today() - timedelta(days=10),
                      return_date=date.today() - timedelta(days=2))
    with patch("app.routes.loans.send_notification") as mock_send:
        response = client.post("/loans/84/remind")
    assert response.status_code == 400
    saved_loan = get_loan(client, book["id"])
    assert saved_loan["return_date"] == (date.today() - timedelta(days=2)).isoformat()
    assert saved_loan["reminded"] is False
    mock_send.assert_not_called()

def test_no_reminder_for_missing_loan(client):
    with patch("app.routes.loans.send_notification") as mock_send:
        response = client.post("/loans/999/remind")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Loan not found"}
    assert client.get("/loans").get_json() == []
    mock_send.assert_not_called()

def test_no_reminder_when_borrower_deleted(client):
    book = add_book(client)
    member = add_member(client)
    add_loan_to_store(85, book["id"], member["id"], date.today() - timedelta(days=4))
    client.delete(f"/members/{member['id']}")
    with patch("app.routes.loans.send_notification") as mock_send:
        response = client.post("/loans/85/remind")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Member not found"}
    assert get_loan(client, book["id"])["reminded"] is False
    mock_send.assert_not_called()

def test_reminder_invalid_recipient_not_recorded(client):
    notification_service.clear_notifications()
    book = add_book(client)
    member = add_member(client, email="no-at-sign.example.com")
    add_loan_to_store(86, book["id"], member["id"], date.today() - timedelta(days=2))
    response = client.post("/loans/86/remind")
    assert response.status_code == 200
    assert response.get_json()["notification_sent"] is False
    assert get_loan(client, book["id"])["reminded"] is False
    assert notification_service.get_notifications() == []
    notification_service.clear_notifications()

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
