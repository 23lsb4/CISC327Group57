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
