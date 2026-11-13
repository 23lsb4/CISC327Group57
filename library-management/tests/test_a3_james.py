from datetime import date, timedelta
from unittest.mock import patch

import notification_service
from app import store
from app.models.loan import Loan

a_book = {"title":"A", "author":"B", "isbn":"100", "total_copies":1}
a_member = {"name":"M", "email":"m@example.com"}

def add_book(client,**override):
    book = {**a_book,**override}
    response = client.post("/books", json=book)
    assert response.status_code == 201
    return response.get_json()

def add_member(client,**override):
    member = {**a_member,**override}
    response = client.post("/members", json=member)
    assert response.status_code == 201
    return response.get_json()

def add_loan_to_store(loan_id, book_id, member_id, due_date, return_date=None):
    store.loans[loan_id] = Loan(id=loan_id, book_id=book_id, member_id=member_id,
                                due_date=due_date, return_date=return_date)

def get_loan(client, book_id):
    return client.get(f"/loans?book_id={book_id}").get_json()[0]

##FEATURE: OVERDUE REMINDER NOTIFICATION

def test_overdue_reminder_sent(client):
    book = add_book(client, title="HiBook")
    member = add_member(client, name="First", email="first@example.com")
    due_date = date.today() - timedelta(days=4)
    add_loan_to_store(70, book["id"], member["id"], due_date)
    with patch("app.routes.loans.send_notification", return_value=True) as mock_send:
        response = client.post("/loans/70/remind")
    assert response.status_code == 200
    data = response.get_json()
    assert data["notification_sent"] is True
    assert data["reminded"] is True
    assert get_loan(client, book["id"])["reminded"] is True
    mock_send.assert_called_once_with(
        "first@example.com", "Overdue book reminder",
        f"'HiBook' was due on {due_date.isoformat()} and is 4 days overdue. Please return it.")

def test_reminder_success_marks_loan_reminded(client, monkeypatch):
    monkeypatch.setattr("app.routes.loans.send_notification",
                        lambda recipient, subject, message: True)
    book = add_book(client)
    member = add_member(client)
    add_loan_to_store(71, book["id"], member["id"], date.today() - timedelta(days=2))
    assert get_loan(client, book["id"])["reminded"] is False
    response = client.post("/loans/71/remind")
    assert response.status_code == 200
    assert response.get_json()["notification_sent"] is True
    saved_loan = get_loan(client, book["id"])
    assert saved_loan["reminded"] is True
    assert saved_loan["overdue"] is True

def test_reminder_goes_to_borrower_only(client):
    book = add_book(client, title="HiBook", total_copies=2)
    first = add_member(client, name="First", email="first@example.com")
    second = add_member(client, name="Second", email="second@example.com")
    add_loan_to_store(72, book["id"], second["id"], date.today() - timedelta(days=6))
    with patch("app.routes.loans.send_notification", return_value=True) as mock_send:
        response = client.post("/loans/72/remind")
    assert response.status_code == 200
    assert response.get_json()["member_id"] == second["id"]
    assert mock_send.call_count == 1
    recipient, subject, message = mock_send.call_args.args
    assert recipient == "second@example.com"
    assert "HiBook" in message
    assert "6 days overdue" in message

def test_reminder_recorded_by_simulator(client):
    notification_service.clear_notifications()
    book = add_book(client, title="HiBook")
    member = add_member(client, name="First", email="first@example.com")
    due_date = date.today() - timedelta(days=3)
    add_loan_to_store(73, book["id"], member["id"], due_date)
    response = client.post("/loans/73/remind")
    assert response.status_code == 200
    assert response.get_json()["notification_sent"] is True
    assert notification_service.get_notifications() == [{
        "recipient": "first@example.com",
        "subject": "[City Library] Overdue book reminder",
        "message": f"'HiBook' was due on {due_date.isoformat()} and is 3 days overdue. Please return it.",
    }]
    notification_service.clear_notifications()

##FEATURE: UI HOME PAGE

def test_ui_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Library Management System" in response.get_data(as_text=True)

##FEATURE: UI BOOKS PAGE

def test_ui_books_page_empty(client):
    response = client.get("/ui/books")
    assert response.status_code == 200
    assert client.get("/books").get_json() == []

def test_ui_books_page_lists_books(client):
    add_book(client, title="HiBook", isbn="1")
    add_book(client, title="ByeBook", isbn="2")
    response = client.get("/ui/books")
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "HiBook" in page
    assert "ByeBook" in page

def test_ui_add_book_saved(client):
    form = {"title":"HiBook", "author":"Hi", "isbn":"1", "total_copies":"3"}
    response = client.post("/ui/books", data=form)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/ui/books")
    books = client.get("/books").get_json()
    assert len(books) == 1
    assert books[0]["title"] == "HiBook"
    assert books[0]["author"] == "Hi"
    assert books[0]["isbn"] == "1"
    assert books[0]["total_copies"] == 3
    assert books[0]["available_copies"] == 3
    assert "HiBook" in client.get("/ui/books").get_data(as_text=True)

def test_ui_delete_book_removed(client):
    book = add_book(client, title="HiBook")
    response = client.post(f"/ui/books/{book['id']}/delete")
    assert response.status_code == 302
    assert client.get("/books").get_json() == []
    assert client.get(f"/books/{book['id']}").status_code == 404
    assert "HiBook" not in client.get("/ui/books").get_data(as_text=True)

def test_ui_delete_book_not_found_changes_nothing(client):
    book = add_book(client, title="HiBook")
    response = client.post("/ui/books/999/delete")
    assert response.status_code == 302
    books = client.get("/books").get_json()
    assert [b["id"] for b in books] == [book["id"]]

##FEATURE: UI MEMBERS PAGE

def test_ui_members_page_lists_members(client):
    add_member(client, name="First", email="first@example.com")
    add_member(client, name="Second", email="second@example.com")
    response = client.get("/ui/members")
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "First" in page
    assert "Second" in page

def test_ui_add_member_saved(client):
    form = {"name":"First", "email":"first@example.com"}
    response = client.post("/ui/members", data=form)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/ui/members")
    members = client.get("/members").get_json()
    assert len(members) == 1
    assert members[0]["name"] == "First"
    assert members[0]["email"] == "first@example.com"
    assert members[0]["membership_date"] == date.today().isoformat()
    assert "First" in client.get("/ui/members").get_data(as_text=True)

def test_ui_delete_member_removed(client):
    member = add_member(client, name="First", email="first@example.com")
    response = client.post(f"/ui/members/{member['id']}/delete")
    assert response.status_code == 302
    assert client.get("/members").get_json() == []
    assert client.get(f"/members/{member['id']}").status_code == 404

def test_ui_delete_member_not_found_changes_nothing(client):
    member = add_member(client, name="First", email="first@example.com")
    response = client.post("/ui/members/999/delete")
    assert response.status_code == 302
    members = client.get("/members").get_json()
    assert [m["id"] for m in members] == [member["id"]]
