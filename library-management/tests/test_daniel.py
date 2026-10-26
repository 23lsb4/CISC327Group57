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
