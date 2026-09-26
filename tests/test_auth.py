from tests.conftest import auth_headers, login, login_json, signup


def test_signup_and_form_login(client):
    response = signup(client)
    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"
    assert response.json()["full_name"] == "Test User"
    assert response.json()["is_admin"] is False

    token = login(client)
    assert token
    assert isinstance(token, str)


def test_json_login(client):
    signup(client, email="jsonuser@example.com", password="SecurePassword123")
    token = login_json(client, email="jsonuser@example.com", password="SecurePassword123")
    assert token
    assert isinstance(token, str)


def test_duplicate_email_is_rejected(client):
    assert signup(client).status_code == 201
    response = signup(client)
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"].lower()


def test_validation_errors(client):
    # Short password
    res1 = signup(client, email="short@example.com", password="short")
    assert res1.status_code == 422

    # Invalid email
    res2 = client.post("/auth/signup", json={"email": "not-an-email", "password": "Password123", "full_name": "Test"})
    assert res2.status_code == 422


def test_wrong_credentials(client):
    signup(client)
    # Wrong password
    res1 = client.post("/auth/login", json={"email": "user@example.com", "password": "WrongPassword"})
    assert res1.status_code == 401

    # Non-existent user
    res2 = client.post("/auth/login", json={"email": "nobody@example.com", "password": "User@12345"})
    assert res2.status_code == 401


def test_me_endpoint(client):
    signup(client)
    token = login(client)
    res = client.get("/auth/me", headers=auth_headers(token))
    assert res.status_code == 200
    assert res.json()["email"] == "user@example.com"


def test_protected_endpoint_requires_auth(client):
    response = client.get("/bookings")
    assert response.status_code == 401


def test_invalid_token_rejected(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer bad-token"})
    assert response.status_code == 401
