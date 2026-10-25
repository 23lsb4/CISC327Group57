from datetime import date

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
