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


def test_list_products_returns_empty_list_initially(client):
    """Products endpoint returns an empty list when no products have been added.

    This is the simplest possible test — it confirms the endpoint exists,
    responds with HTTP 200, and that the store starts clean for every test
    (thanks to the reset() call in conftest.py).
    """
    response = client.get("/products")
    assert response.status_code == 200
    assert response.get_json() == []


def test_create_product_and_check_stock_level(client):
    """A product POSTed to /products can have its stock level queried.

    This is the create-then-verify pattern: send a POST, use the returned id
    to make a follow-up GET, and confirm the data is consistent. You can
    extend this idea to test stock changes after transactions (IN/OUT), or
    to test edge cases like what happens when quantity_on_hand reaches 0.
    """
    payload = {
        "name": "Widget A",
        "sku": "WGT-001",
        "unit_price": 9.99,
        "quantity_on_hand": 50,
        "reorder_level": 10,
    }
    create_resp = client.post("/products", json=payload)
    assert create_resp.status_code == 201
    product_id = create_resp.get_json()["id"]

    stock_resp = client.get(f"/products/{product_id}/stock-level")
    assert stock_resp.status_code == 200
    assert stock_resp.get_json()["quantity_on_hand"] == 50
