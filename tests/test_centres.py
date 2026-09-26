from decimal import Decimal

from tests.conftest import auth_headers, login, login_admin, signup


def test_public_can_list_centres(client):
    admin_token = login_admin(client)
    client.post(
        "/centres",
        headers=auth_headers(admin_token),
        json={"name": "Centre A", "location": "Noida"},
    )

    # Public unauthenticated request
    res = client.get("/centres")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Centre A"


def test_search_centres_by_location(client):
    admin_token = login_admin(client)
    client.post("/centres", headers=auth_headers(admin_token), json={"name": "Alpha", "location": "Noida"})
    client.post("/centres", headers=auth_headers(admin_token), json={"name": "Beta", "location": "Bengaluru"})

    res = client.get("/centres?search=Noida")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["name"] == "Alpha"


def test_get_centre_by_id(client):
    admin_token = login_admin(client)
    create_res = client.post(
        "/centres",
        headers=auth_headers(admin_token),
        json={"name": "Centre One", "location": "Delhi"},
    )
    centre_id = create_res.json()["id"]

    res = client.get(f"/centres/{centre_id}")
    assert res.status_code == 200
    assert res.json()["id"] == centre_id
    assert res.json()["name"] == "Centre One"


def test_get_nonexistent_centre(client):
    res = client.get("/centres/99999")
    assert res.status_code == 404


def test_admin_create_and_update_centre(client):
    admin_token = login_admin(client)

    # Create
    res = client.post(
        "/centres",
        headers=auth_headers(admin_token),
        json={"name": "New Diagnostics", "location": "Mumbai"},
    )
    assert res.status_code == 201
    centre_id = res.json()["id"]

    # Update
    update_res = client.put(
        f"/centres/{centre_id}",
        headers=auth_headers(admin_token),
        json={"name": "Updated Diagnostics", "location": "Mumbai Suburb"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Updated Diagnostics"
    assert update_res.json()["location"] == "Mumbai Suburb"


def test_non_admin_cannot_create_or_modify_centre(client):
    signup(client, email="regular@example.com")
    token = login(client, email="regular@example.com")

    # Attempt create
    res = client.post(
        "/centres",
        headers=auth_headers(token),
        json={"name": "Unauthorized Centre", "location": "City"},
    )
    assert res.status_code == 403


def test_admin_manage_tests(client):
    admin_token = login_admin(client)
    centre = client.post(
        "/centres",
        headers=auth_headers(admin_token),
        json={"name": "Health Lab", "location": "Gurgaon"},
    ).json()
    centre_id = centre["id"]

    # Add test
    add_res = client.post(
        f"/centres/{centre_id}/tests",
        headers=auth_headers(admin_token),
        json={"name": "Blood Sugar Fasting", "description": "Fasting blood sugar test", "price": "150.00"},
    )
    assert add_res.status_code == 201
    test_id = add_res.json()["id"]
    assert add_res.json()["price"] == "150.00"

    # List tests for centre
    tests_res = client.get(f"/centres/{centre_id}/tests")
    assert tests_res.status_code == 200
    assert len(tests_res.json()) == 1

    # Get single test
    single_res = client.get(f"/centres/{centre_id}/tests/{test_id}")
    assert single_res.status_code == 200
    assert single_res.json()["name"] == "Blood Sugar Fasting"

    # Update test
    upd_res = client.put(
        f"/centres/{centre_id}/tests/{test_id}",
        headers=auth_headers(admin_token),
        json={"price": "180.00"},
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["price"] == "180.00"

    # Delete test
    del_res = client.delete(
        f"/centres/{centre_id}/tests/{test_id}",
        headers=auth_headers(admin_token),
    )
    assert del_res.status_code == 204


def test_invalid_test_creation(client):
    admin_token = login_admin(client)
    centre = client.post(
        "/centres",
        headers=auth_headers(admin_token),
        json={"name": "Test Lab", "location": "Pune"},
    ).json()

    # Negative price rejected
    res = client.post(
        f"/centres/{centre['id']}/tests",
        headers=auth_headers(admin_token),
        json={"name": "Test", "price": "-10.00"},
    )
    assert res.status_code == 422
