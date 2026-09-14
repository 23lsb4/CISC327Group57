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


def test_list_rentals_returns_empty_list_initially(client):
    """Rentals endpoint returns an empty list when no rentals have been made.

    This is the simplest possible test — it confirms the endpoint exists,
    responds with HTTP 200, and that the store starts clean for every test
    (thanks to the reset() call in conftest.py).
    """
    response = client.get("/rentals")
    assert response.status_code == 200
    assert response.get_json() == []


def test_create_equipment_and_check_availability(client):
    """Equipment POSTed to /equipment can have its availability queried.

    This is the create-then-verify pattern using the /availability sub-endpoint.
    You can extend this idea to test what happens to available_units after a
    checkout, or what the availability endpoint returns after equipment is
    marked out-of-service — think about whether the app behaves the way
    your requirements say it should.
    """
    payload = {
        "name": "Extension Ladder",
        "category": "Climbing",
        "total_units": 3,
    }
    create_resp = client.post("/equipment", json=payload)
    assert create_resp.status_code == 201
    equipment_id = create_resp.get_json()["id"]

    avail_resp = client.get(f"/equipment/{equipment_id}/availability")
    assert avail_resp.status_code == 200
    data = avail_resp.get_json()
    assert data["available_units"] == 3
    assert data["is_available"] is True
