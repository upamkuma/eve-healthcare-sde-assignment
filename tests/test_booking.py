from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.db.session import SessionLocal
from app.models.diagnostic import DiagnosticCentre, DiagnosticTest
from tests.conftest import auth_headers, login, login_admin, signup


def seed_catalog():
    db = SessionLocal()
    centre = DiagnosticCentre(name="Test Centre", location="Noida")
    db.add(centre)
    db.flush()
    test = DiagnosticTest(
        centre_id=centre.id,
        name="CBC",
        description="Test",
        price=Decimal("500.00"),
    )
    db.add(test)
    db.commit()
    db.refresh(centre)
    db.refresh(test)
    db.close()
    return centre.id, test.id


def test_booking_uses_server_side_price_and_pending_status(client):
    signup(client)
    token = login(client)
    centre_id, test_id = seed_catalog()

    response = client.post(
        "/bookings",
        headers=auth_headers(token),
        json={
            "test_id": test_id,
            "centre_id": centre_id,
            "appointment_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == "500.00"
    assert data["status"] == "PENDING"
    assert data["centre_id"] == centre_id
    assert data["test_id"] == test_id


def test_mismatched_test_and_centre_is_rejected(client):
    signup(client)
    token = login(client)

    db = SessionLocal()
    centre1 = DiagnosticCentre(name="Centre A", location="Noida")
    centre2 = DiagnosticCentre(name="Centre B", location="Delhi")
    db.add_all([centre1, centre2])
    db.flush()
    test = DiagnosticTest(centre_id=centre1.id, name="CBC", price=Decimal("500.00"))
    db.add(test)
    db.commit()
    db.refresh(centre2)
    db.refresh(test)
    db.close()

    response = client.post(
        "/bookings",
        headers=auth_headers(token),
        json={
            "test_id": test.id,
            "centre_id": centre2.id,
            "appointment_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 400
    assert "Selected test does not belong" in response.json()["detail"]


def test_booking_owner_only_access(client):
    signup(client, email="one@example.com")
    token_one = login(client, email="one@example.com")

    signup(client, email="two@example.com")
    token_two = login(client, email="two@example.com")

    centre_id, test_id = seed_catalog()

    response = client.post(
        "/bookings",
        headers=auth_headers(token_one),
        json={
            "test_id": test_id,
            "centre_id": centre_id,
            "appointment_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        },
    )
    booking_id = response.json()["id"]

    # User two attempts to view user one's booking
    response = client.get(
        f"/bookings/{booking_id}",
        headers=auth_headers(token_two),
    )
    assert response.status_code == 403

    # Admin CAN view booking
    admin_token = login_admin(client)
    admin_res = client.get(
        f"/bookings/{booking_id}",
        headers=auth_headers(admin_token),
    )
    assert admin_res.status_code == 200


def test_cancel_booking(client):
    signup(client)
    token = login(client)
    centre_id, test_id = seed_catalog()

    response = client.post(
        "/bookings",
        headers=auth_headers(token),
        json={
            "test_id": test_id,
            "centre_id": centre_id,
            "appointment_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        },
    )
    booking_id = response.json()["id"]

    response = client.post(
        f"/bookings/{booking_id}/cancel",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"

    # Cannot cancel again
    second_cancel = client.post(
        f"/bookings/{booking_id}/cancel",
        headers=auth_headers(token),
    )
    assert second_cancel.status_code == 409


def test_past_appointment_date_rejected(client):
    signup(client)
    token = login(client)
    centre_id, test_id = seed_catalog()

    response = client.post(
        "/bookings",
        headers=auth_headers(token),
        json={
            "test_id": test_id,
            "centre_id": centre_id,
            "appointment_at": "2020-01-01T10:00:00Z",
        },
    )
    assert response.status_code == 400
    assert "future" in response.json()["detail"].lower()


def test_naive_appointment_date_accepted(client):
    signup(client)
    token = login(client)
    centre_id, test_id = seed_catalog()

    # ISO string without 'Z' or timezone offset
    future_naive = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S")
    response = client.post(
        "/bookings",
        headers=auth_headers(token),
        json={
            "test_id": test_id,
            "centre_id": centre_id,
            "appointment_at": future_naive,
        },
    )
    assert response.status_code == 201


def test_nonexistent_test_or_centre_rejected(client):
    signup(client)
    token = login(client)
    centre_id, _ = seed_catalog()

    res = client.post(
        "/bookings",
        headers=auth_headers(token),
        json={
            "test_id": 99999,
            "centre_id": centre_id,
            "appointment_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        },
    )
    assert res.status_code == 404
