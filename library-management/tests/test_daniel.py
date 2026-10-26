from datetime import date, timedelta

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

def get_member(client, member_id):
    return client.get(f"/members/{member_id}")

def checkout(client, book_id, member_id):
    return client.post("/loans", json={"book_id":book_id, "member_id":member_id})

def get_copies(client, book_id):
    return client.get(f"/books/{book_id}").get_json()["available_copies"]

##FEATURE: LIST MEMBERS

def test_list_members_returns_all_in_order(client):
    add_member(client, name="Ann", email="ann@example.com")
    add_member(client, name="Bo", email="bo@example.com")
    members = client.get("/members").get_json()
    assert [m["name"] for m in members] == ["Ann", "Bo"]
    assert [m["email"] for m in members] == ["ann@example.com", "bo@example.com"]
    assert [m["id"] for m in members] == [1, 2]

def test_list_members_excludes_deleted(client):
    ann = add_member(client, name="Ann", email="ann@example.com")
    add_member(client, name="Bo", email="bo@example.com")
    client.delete(f"/members/{ann['id']}")
    members = client.get("/members").get_json()
    assert [m["name"] for m in members] == ["Bo"]

##FEATURE: CREATE A MEMBER

def test_create_member_fields_and_saved(client):
    member = add_member(client, name="Ann", email="ann@example.com")
    assert member["name"] == "Ann"
    assert member["email"] == "ann@example.com"
    assert member["membership_date"] == date.today().isoformat()
    assert get_member(client, member["id"]).get_json() == member

def test_create_member_ids_are_unique(client):
    ids = [add_member(client, email=f"m{n}@example.com")["id"] for n in range(5)]
    assert ids == [1, 2, 3, 4, 5]

# FR-011: the system must hold at least 800 active members
def test_create_800_members(client):
    for n in range(800):
        add_member(client, email=f"m{n}@example.com")
    members = client.get("/members").get_json()
    assert len(members) == 800
    assert members[-1]["email"] == "m799@example.com"

##FEATURE: GET ONE MEMBER

def test_get_member_matches_record(client):
    add_member(client, name="Ann", email="ann@example.com")
    bo = add_member(client, name="Bo", email="bo@example.com")
    response = get_member(client, bo["id"])
    assert response.status_code == 200
    assert response.get_json()["name"] == "Bo"
    assert response.get_json()["email"] == "bo@example.com"

def test_get_member_not_found(client):
    response = get_member(client, 999)
    assert response.status_code == 404
    assert "error" in response.get_json()

##FEATURE: UPDATE A MEMBER

def test_update_member_saved_and_keeps_other_fields(client):
    member = add_member(client, name="Ann", email="ann@example.com")
    response = client.put(f"/members/{member['id']}", json={"email":"new@example.com"})
    assert response.status_code == 200
    saved_member = get_member(client, member["id"]).get_json()
    assert saved_member["email"] == "new@example.com"
    assert saved_member["name"] == "Ann"
    assert saved_member["membership_date"] == member["membership_date"]

def test_update_member_not_found(client):
    response = client.put("/members/999", json={"name":"X"})
    assert response.status_code == 404
    assert client.get("/members").get_json() == []

##FEATURE: DELETE A MEMBER

def test_delete_member_removed(client):
    member = add_member(client)
    response = client.delete(f"/members/{member['id']}")
    assert response.status_code == 204
    assert get_member(client, member["id"]).status_code == 404
    assert client.get("/members").get_json() == []

def test_delete_member_not_found_or_twice(client):
    member = add_member(client)
    assert client.delete("/members/999").status_code == 404
    client.delete(f"/members/{member['id']}")
    assert client.delete(f"/members/{member['id']}").status_code == 404

##FEATURE: CHECK OUT A BOOK

# FR-016: a checkout records the book, member, checkout date, and due date
def test_checkout_records_loan_details(client):
    book = add_book(client)
    member = add_member(client)
    response = checkout(client, book["id"], member["id"])
    assert response.status_code == 201
    loan = response.get_json()
    assert loan["book_id"] == book["id"]
    assert loan["member_id"] == member["id"]
    assert loan["loan_date"] == date.today().isoformat()
    assert loan["due_date"] == (date.today() + timedelta(days=14)).isoformat()
    assert loan["return_date"] is None

# FR-003: checking out a book lowers its available copies
def test_checkout_lowers_available_copies(client):
    book = add_book(client, total_copies=2)
    member = add_member(client)
    checkout(client, book["id"], member["id"])
    saved_book = client.get(f"/books/{book['id']}").get_json()
    assert saved_book["available_copies"] == 1
    assert saved_book["total_copies"] == 2

def test_checkout_book_not_found(client):
    member = add_member(client)
    response = checkout(client, 999, member["id"])
    assert response.status_code == 404
    assert client.get("/loans").get_json() == []

# FR-015: staff can only check out an *available* book
def test_checkout_rejected_when_no_copies_left(client):
    book = add_book(client, total_copies=1)
    first = add_member(client, email="m1@example.com")
    second = add_member(client, email="m2@example.com")
    checkout(client, book["id"], first["id"])
    response = checkout(client, book["id"], second["id"])
    assert 400 <= response.status_code < 500
    assert get_copies(client, book["id"]) == 0

# FR-015: a book can only be checked out to a library member
def test_checkout_rejected_for_unknown_member(client):
    book = add_book(client)
    response = checkout(client, book["id"], 999)
    assert response.status_code == 404
    assert get_copies(client, book["id"]) == 1

##FEATURE: LOOK UP LOANS

def test_lookup_loans_without_filter_returns_all(client):
    book = add_book(client, total_copies=2)
    ann = add_member(client, email="ann@example.com")
    bo = add_member(client, email="bo@example.com")
    checkout(client, book["id"], ann["id"])
    checkout(client, book["id"], bo["id"])
    loans = client.get("/loans").get_json()
    assert [l["member_id"] for l in loans] == [ann["id"], bo["id"]]

def test_lookup_loans_by_book_id(client):
    book_1 = add_book(client, isbn="1")
    book_2 = add_book(client, isbn="2")
    member = add_member(client)
    checkout(client, book_1["id"], member["id"])
    checkout(client, book_2["id"], member["id"])
    loans = client.get(f"/loans?book_id={book_2['id']}").get_json()
    assert len(loans) == 1
    assert loans[0]["book_id"] == book_2["id"]
    assert client.get("/loans?book_id=999").get_json() == []

# FR-019: a member must be able to see their own borrowed books.
# Ann borrows book 2 and Bo borrows book 1, so a member_id filter that
# compares against book_id instead would return Bo's loan for Ann.
def test_lookup_loans_by_member_id(client):
    book_1 = add_book(client, isbn="1")
    book_2 = add_book(client, isbn="2")
    ann = add_member(client, email="ann@example.com")
    bo = add_member(client, email="bo@example.com")
    checkout(client, book_2["id"], ann["id"])
    checkout(client, book_1["id"], bo["id"])
    loans = client.get(f"/loans?member_id={ann['id']}").get_json()
    assert [l["member_id"] for l in loans] == [ann["id"]]
    assert loans[0]["book_id"] == book_2["id"]

# FR-018: looked-up loans show the due date, and the return once recorded
def test_lookup_loan_reflects_return(client):
    book = add_book(client)
    member = add_member(client)
    loan = checkout(client, book["id"], member["id"]).get_json()
    client.put(f"/loans/{loan['id']}/return")
    saved_loan = client.get(f"/loans?book_id={book['id']}").get_json()[0]
    assert saved_loan["due_date"] == loan["due_date"]
    assert saved_loan["return_date"] == date.today().isoformat()

##FEATURE: PLACE A HOLD

def place_hold(client, book_id, member_id):
    return client.post("/reservations", json={"book_id":book_id, "member_id":member_id})

# FR-020: a member can place a hold on a checked-out book
def test_place_hold_on_checked_out_book(client):
    book = add_book(client)
    borrower = add_member(client, email="m1@example.com")
    waiting = add_member(client, email="m2@example.com")
    checkout(client, book["id"], borrower["id"])
    response = place_hold(client, book["id"], waiting["id"])
    assert response.status_code == 201
    hold = response.get_json()
    assert hold["book_id"] == book["id"]
    assert hold["member_id"] == waiting["id"]
    assert hold["reservation_date"] == date.today().isoformat()
    assert hold["fulfilled"] is False
    assert client.get("/reservations").get_json() == [hold]

def test_place_hold_unknown_book_or_member(client):
    book = add_book(client)
    member = add_member(client)
    assert place_hold(client, 999, member["id"]).status_code == 404
    assert place_hold(client, book["id"], 999).status_code == 404
    assert client.get("/reservations").get_json() == []

# FR-021: the waiting list must stay ordered, so one member
# holding the same book twice would take up two places in line
def test_place_hold_twice_same_member_rejected(client):
    book = add_book(client)
    borrower = add_member(client, email="m1@example.com")
    waiting = add_member(client, email="m2@example.com")
    checkout(client, book["id"], borrower["id"])
    place_hold(client, book["id"], waiting["id"])
    response = place_hold(client, book["id"], waiting["id"])
    assert 400 <= response.status_code < 500
    assert len(client.get(f"/reservations?book_id={book['id']}").get_json()) == 1

# FR-004/FR-020: a returned book with an outstanding hold is not simply
# available, so a member who is not first in line should not get it
def test_hold_blocks_checkout_by_other_member(client):
    book = add_book(client)
    borrower = add_member(client, email="m1@example.com")
    waiting = add_member(client, email="m2@example.com")
    other = add_member(client, email="m3@example.com")
    loan = checkout(client, book["id"], borrower["id"]).get_json()
    place_hold(client, book["id"], waiting["id"])
    client.put(f"/loans/{loan['id']}/return")
    response = checkout(client, book["id"], other["id"])
    assert 400 <= response.status_code < 500
    assert get_copies(client, book["id"]) == 1

##FEATURE: LIST RESERVATIONS

# FR-021: holds on the same book are listed in the order they were placed
def test_list_reservations_in_order_placed(client):
    book = add_book(client)
    borrower = add_member(client, email="m1@example.com")
    second = add_member(client, email="m2@example.com")
    third = add_member(client, email="m3@example.com")
    checkout(client, book["id"], borrower["id"])
    place_hold(client, book["id"], second["id"])
    place_hold(client, book["id"], third["id"])
    holds = client.get(f"/reservations?book_id={book['id']}").get_json()
    assert [h["member_id"] for h in holds] == [second["id"], third["id"]]

def test_list_reservations_filter_by_member_and_book(client):
    book_1 = add_book(client, isbn="1")
    book_2 = add_book(client, isbn="2")
    ann = add_member(client, email="ann@example.com")
    bo = add_member(client, email="bo@example.com")
    place_hold(client, book_1["id"], ann["id"])
    place_hold(client, book_2["id"], ann["id"])
    place_hold(client, book_1["id"], bo["id"])
    ann_holds = client.get(f"/reservations?member_id={ann['id']}").get_json()
    assert [h["book_id"] for h in ann_holds] == [book_1["id"], book_2["id"]]
    both = client.get(f"/reservations?book_id={book_1['id']}&member_id={bo['id']}").get_json()
    assert len(both) == 1
    assert both[0]["member_id"] == bo["id"]

def test_list_reservations_empty(client):
    assert client.get("/reservations").get_json() == []
    add_book(client)
    assert client.get("/reservations?book_id=1").get_json() == []

##ENHANCEMENT: HOLD QUEUE (FR-004, FR-020, FR-021, FR-022)

def hold_position(client, reservation_id):
    return client.get(f"/reservations/{reservation_id}/position")

def test_first_in_line_checks_out_and_queue_moves_up(client):
    book = add_book(client)
    borrower = add_member(client, email="m1@example.com")
    first = add_member(client, email="m2@example.com")
    second = add_member(client, email="m3@example.com")
    loan = checkout(client, book["id"], borrower["id"]).get_json()
    hold_1 = place_hold(client, book["id"], first["id"]).get_json()
    hold_2 = place_hold(client, book["id"], second["id"]).get_json()
    client.put(f"/loans/{loan['id']}/return")
    assert checkout(client, book["id"], second["id"]).status_code == 409
    response = checkout(client, book["id"], first["id"])
    assert response.status_code == 201
    assert response.get_json()["member_id"] == first["id"]
    holds = client.get(f"/reservations?book_id={book['id']}").get_json()
    assert [h["fulfilled"] for h in holds] == [True, False]
    assert hold_position(client, hold_2["id"]).get_json()["position"] == 1
    assert hold_position(client, hold_1["id"]).status_code == 400

def test_hold_position_reports_place_in_line(client):
    book = add_book(client)
    borrower = add_member(client, email="m1@example.com")
    first = add_member(client, email="m2@example.com")
    second = add_member(client, email="m3@example.com")
    checkout(client, book["id"], borrower["id"])
    hold_1 = place_hold(client, book["id"], first["id"]).get_json()
    hold_2 = place_hold(client, book["id"], second["id"]).get_json()
    data = hold_position(client, hold_2["id"]).get_json()
    assert data["member_id"] == second["id"]
    assert data["position"] == 2
    assert data["queue_length"] == 2
    assert hold_position(client, hold_1["id"]).get_json()["position"] == 1
    assert hold_position(client, 999).status_code == 404

def test_spare_copies_not_blocked_by_hold(client):
    book = add_book(client, total_copies=3)
    borrower = add_member(client, email="m1@example.com")
    waiting = add_member(client, email="m2@example.com")
    other = add_member(client, email="m3@example.com")
    checkout(client, book["id"], borrower["id"])
    place_hold(client, book["id"], waiting["id"])
    assert checkout(client, book["id"], other["id"]).status_code == 201
    assert get_copies(client, book["id"]) == 1
    assert checkout(client, book["id"], borrower["id"]).status_code == 409
    assert checkout(client, book["id"], waiting["id"]).status_code == 201
    assert get_copies(client, book["id"]) == 0
