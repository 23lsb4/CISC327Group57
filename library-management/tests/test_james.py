from datetime import date, timedelta
 
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

def checkout_book(client, book_id, member_id):
    response = client.post("/loans", json={"book_id":book_id, "member_id":member_id})
    return response.get_json()
    
def get_copies(client, book_id):
    return client.get(f"/books/{book_id}").get_json()["available_copies"]

def add_loan_to_store(loan_id, book_id, member_id, due_date, return_date=None):
    store.loans[loan_id] = Loan(id=loan_id, book_id=book_id, member_id=member_id,
                                due_date=due_date, return_date=return_date)

##FEATURE: LIST BOOKS

def test_list_books_return_all_added_books_fields(client): 
    add_book(client, title="HiBook", author ="Hi", isbn="1", total_copies=1)
    add_book(client, title="ByeBook", author ="Bye", isbn="2", total_copies=4)
    books = client.get("/books").get_json()
    expected_title = ["HiBook","ByeBook"]
    expected_isbn = ["1","2"]
    n = 0
    for book in books:
        assert book["title"] == expected_title[n]
        assert book["isbn"] == expected_isbn[n]
        n+=1
    assert books[1]["available_copies"] == 4

##FEATURE: SEARCH BOOKS

def test_search_match_title_case(client):
    add_book(client, title="HiBook", isbn="1")
    add_book(client, title="ByeBook", isbn="2")
    search_result = client.get("/books?search=HIBOOK").get_json()
    for book in search_result:
        assert book["title"] == "HiBook"

def test_search_match_partial_text(client):
    add_book(client, title="HiBook", isbn="1")
    add_book(client, title="ByeBook", author = "John Smith", isbn="2")
    search_result = client.get("/books?search=john").get_json()
    for book in search_result:
        assert book["title"] == "ByeBook"

def test_search_no_matches(client):
    add_book(client)
    search_result = client.get("/books?search=_")
    assert search_result.status_code == 200
    assert search_result.get_json() == []

def test_search_updated_title_consistency(client):
    book = add_book(client, title="HiBook")
    client.put(f"/books/{book['id']}",json={"title":"ByeBook"})
    assert client.get("/books?search=HiBook").get_json() == []
    assert len(client.get("/books?search=ByeBook").get_json()) == 1

##FEATURE: ADD A BOOK

def test_add_book_correct_fields(client):
    book = add_book(client, title="HiBook", author ="Hi", isbn="1", total_copies=1)
    assert book["title"] == "HiBook"
    assert book["author"] == "Hi"
    assert book["isbn"] == "1"
    assert book["total_copies"] == 1

def test_add_book_available_and_saved(client):
    book = add_book(client, total_copies=4)
    assert book["available_copies"] == 4
    saved_book = client.get(f"/books/{book['id']}").get_json()
    assert saved_book == book

def test_add_book_no_negative_copies(client):
    response = client.post("/books",json={**a_book,"total_copies":-1})
    assert 400 <= response.status_code < 500

def test_add_book_empty_title(client):
    response = client.post("/books", json={**a_book, "title":""})
    assert 400 <= response.status_code < 500

##FEATURE: VIEW ONE BOOK

def test_view_book_matches_record(client):
    book = add_book(client, title="HiBook", isbn="1")
    response = client.get(f"/books/{book['id']}")
    assert response.status_code == 200
    assert response.get_json()["title"] == "HiBook"
 
def test_view_book_not_found(client):
    response = client.get("/books/999")
    assert response.status_code == 404
    assert "error" in response.get_json()
 
def test_view_book_hides_borrower(client):
    book = add_book(client)
    member = add_member(client)
    checkout_book(client, book["id"], member["id"])
    data = client.get(f"/books/{book['id']}").get_json()
    assert data["available_copies"] == 0
    assert "member_id" not in data
    assert "borrower" not in data

##FEATURE: UPDATE A BOOK
 
def test_update_book_saved(client):
    book = add_book(client)
    response = client.put(f"/books/{book['id']}",json={"title":"ByeBook"})
    assert response.status_code == 200
    saved_book = client.get(f"/books/{book['id']}").get_json()
    assert saved_book["title"] == "ByeBook"
 
def test_update_book_not_found(client):
    response = client.put("/books/999",json={"title":"ByeBook"})
    assert response.status_code == 404
 
def test_update_available_copies_above_total(client):
    book = add_book(client, total_copies=1)
    client.put(f"/books/{book['id']}",json={"available_copies":99})
    saved_book = client.get(f"/books/{book['id']}").get_json()
    assert saved_book["available_copies"] <= saved_book["total_copies"]
 
##FEATURE: DELETE A BOOK
 
def test_delete_book_removed(client):
    book = add_book(client)
    response = client.delete(f"/books/{book['id']}")
    assert response.status_code == 204
    assert client.get(f"/books/{book['id']}").status_code == 404
    assert client.get("/books").get_json() == []
 
def test_delete_book_not_found_or_twice(client):
    book = add_book(client)
    assert client.delete("/books/999").status_code == 404
    client.delete(f"/books/{book['id']}")
    assert client.delete(f"/books/{book['id']}").status_code == 404

##FEATURE: RETURN A LOAN
 
def test_return_loan_date_and_copies(client):
    book = add_book(client)
    member = add_member(client)
    loan = checkout_book(client, book["id"], member["id"])
    assert get_copies(client, book["id"]) == 0
    response = client.put(f"/loans/{loan['id']}/return")
    assert response.status_code == 200
    assert response.get_json()["return_date"] == date.today().isoformat()
    assert get_copies(client, book["id"]) == 1
 
def test_return_one_of_two_loans(client):
    book = add_book(client, total_copies=2)
    member_1 = add_member(client, email="m1@example.com")
    member_2 = add_member(client, email="m2@example.com")
    loan_1 = checkout_book(client, book["id"], member_1["id"])
    checkout_book(client, book["id"], member_2["id"])
    assert get_copies(client, book["id"]) == 0
    client.put(f"/loans/{loan_1['id']}/return")
    assert get_copies(client, book["id"]) == 1
 
def test_return_twice_rejected(client):
    book = add_book(client)
    member = add_member(client)
    loan = checkout_book(client, book["id"], member["id"])
    client.put(f"/loans/{loan['id']}/return")
    response = client.put(f"/loans/{loan['id']}/return")
    assert response.status_code == 400
    assert get_copies(client, book["id"]) == 1
 
def test_return_loan_not_found(client):
    response = client.put("/loans/999/return")
    assert response.status_code == 404

##FEATURE: RENEW A LOAN
 
def test_renew_adds_14_days(client):
    book = add_book(client)
    member = add_member(client)
    loan = checkout_book(client, book["id"], member["id"])
    old_due_date = date.fromisoformat(loan["due_date"])
    response = client.put(f"/loans/{loan['id']}/renew")
    assert response.status_code == 200
    new_due_date = date.fromisoformat(response.get_json()["due_date"])
    assert new_due_date == old_due_date + timedelta(days=14)
    saved_loan = client.get(f"/loans?book_id={book['id']}").get_json()[0]
    assert saved_loan["due_date"] == new_due_date.isoformat()
 
def test_renew_loan_not_found(client):
    response = client.put("/loans/999/renew")
    assert response.status_code == 404
 
def test_renew_after_return_rejected(client):
    book = add_book(client)
    member = add_member(client)
    loan = checkout_book(client, book["id"], member["id"])
    client.put(f"/loans/{loan['id']}/return")
    response = client.put(f"/loans/{loan['id']}/renew")
    assert response.status_code == 400
 
def test_renew_blocked_by_hold(client):
    book = add_book(client)
    borrower = add_member(client, email="m1@example.com")
    waiting = add_member(client, email="m2@example.com")
    loan = checkout_book(client, book["id"], borrower["id"])
    client.post("/reservations", json={"book_id":book["id"], "member_id":waiting["id"]})
    response = client.put(f"/loans/{loan['id']}/renew")
    assert response.status_code != 200
 
##FEATURE: CALCULATE A FINE
 
def test_fine_zero_when_not_due(client):
    book = add_book(client)
    member = add_member(client)
    loan = checkout_book(client, book["id"], member["id"])
    data = client.get(f"/loans/{loan['id']}/fine").get_json()
    assert data["loan_id"] == loan["id"]
    assert data["fine_amount"] == 0
 
def test_fine_per_day_overdue(client):
    book = add_book(client)
    member = add_member(client)
    add_loan_to_store(50, book["id"], member["id"], date.today() - timedelta(days=5))
    data = client.get("/loans/50/fine").get_json()
    assert data["fine_amount"] == 1.25
 
def test_fine_loan_not_found(client):
    response = client.get("/loans/999/fine")
    assert response.status_code == 404
 
def test_fine_lower_after_renewal(client):
    book = add_book(client)
    member = add_member(client)
    add_loan_to_store(52, book["id"], member["id"], date.today() - timedelta(days=20))
    fine_before = client.get("/loans/52/fine").get_json()["fine_amount"]
    client.put("/loans/52/renew")
    fine_after = client.get("/loans/52/fine").get_json()["fine_amount"]
    assert fine_before == 5.0
    assert fine_after == 1.5
 
def test_fine_stops_at_return_date(client):
    book = add_book(client)
    member = add_member(client)
    due_date = date.today() - timedelta(days=10)
    add_loan_to_store(53, book["id"], member["id"], due_date, return_date=due_date + timedelta(days=2))
    data = client.get("/loans/53/fine").get_json()
    assert data["fine_amount"] == 0.5

##ENHANCEMENT: OVERDUE LOAN TRACKING
 
def test_overdue_loan_listed_with_days(client):
    book = add_book(client)
    member = add_member(client)
    add_loan_to_store(60, book["id"], member["id"], date.today() - timedelta(days=5))
    response = client.get("/loans/overdue")
    assert response.status_code == 200
    overdue_loans = response.get_json()
    assert len(overdue_loans) == 1
    assert overdue_loans[0]["id"] == 60
    assert overdue_loans[0]["overdue"] is True
    assert overdue_loans[0]["days_overdue"] == 5
 
def test_overdue_loan_due_today_not_overdue(client):
    book = add_book(client)
    member = add_member(client)
    add_loan_to_store(61, book["id"], member["id"], date.today())
    assert client.get("/loans/overdue").get_json() == []
    saved_loan = client.get(f"/loans?book_id={book['id']}").get_json()[0]
    assert saved_loan["overdue"] is False
    assert saved_loan["days_overdue"] == 0
 
def test_overdue_loan_removed_after_return(client):
    book = add_book(client)
    member = add_member(client)
    add_loan_to_store(62, book["id"], member["id"], date.today() - timedelta(days=3))
    assert len(client.get("/loans/overdue").get_json()) == 1
    client.put("/loans/62/return")
    assert client.get("/loans/overdue").get_json() == []
    saved_loan = client.get(f"/loans?book_id={book['id']}").get_json()[0]
    assert saved_loan["overdue"] is False
    assert saved_loan["days_overdue"] == 0
 
def test_overdue_loans_member_filter(client):
    book = add_book(client, total_copies=2)
    member_1 = add_member(client, email="m1@example.com")
    member_2 = add_member(client, email="m2@example.com")
    add_loan_to_store(63, book["id"], member_1["id"], date.today() - timedelta(days=4))
    add_loan_to_store(64, book["id"], member_2["id"], date.today() - timedelta(days=2))
    result_1 = client.get(f"/loans/overdue?member_id={member_1['id']}").get_json()
    result_2 = client.get(f"/loans/overdue?member_id={member_2['id']}").get_json()
    assert [loan["id"] for loan in result_1] == [63]
    assert [loan["id"] for loan in result_2] == [64]
    response = client.get("/loans/overdue?member_id=999")
    assert response.status_code == 200
    assert response.get_json() == []
 
def test_overdue_loans_oldest_first(client):
    book = add_book(client, total_copies=3)
    member = add_member(client)
    add_loan_to_store(65, book["id"], member["id"], date.today() - timedelta(days=3))
    add_loan_to_store(66, book["id"], member["id"], date.today() - timedelta(days=9))
    add_loan_to_store(67, book["id"], member["id"], date.today() - timedelta(days=6))
    overdue_loans = client.get("/loans/overdue").get_json()
    assert [loan["id"] for loan in overdue_loans] == [66, 67, 65]
 
def test_new_checkout_not_overdue(client):
    book = add_book(client)
    member = add_member(client)
    loan = checkout_book(client, book["id"], member["id"])
    assert loan["overdue"] is False
    assert loan["days_overdue"] == 0
    assert client.get("/loans/overdue").get_json() == []
 
def test_loans_list_marks_overdue_loans(client):
    book = add_book(client, total_copies=2)
    member = add_member(client)
    add_loan_to_store(68, book["id"], member["id"], date.today() - timedelta(days=2))
    add_loan_to_store(69, book["id"], member["id"], date.today() + timedelta(days=5))
    loans = {loan["id"]: loan for loan in client.get("/loans").get_json()}
    assert loans[68]["overdue"] is True
    assert loans[68]["days_overdue"] == 2
    assert loans[69]["overdue"] is False
    assert loans[69]["days_overdue"] == 0
