from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.db.session import SessionLocal
from app.models.diagnostic import DiagnosticCentre, DiagnosticTest
from tests.conftest import auth_headers, login, login_admin, signup


def seed_catalog():
    db = SessionLocal()
    centre = DiagnosticCentre(name="Payment Centre", location="Noida")
    db.add(centre)
    db.flush()
    test = DiagnosticTest(
        centre_id=centre.id,
        name="CBC",
        price=Decimal("500.00"),
    )
    db.add(test)
    db.commit()
    db.refresh(centre)
    db.refresh(test)
    db.close()
    return centre.id, test.id


def create_booking(client):
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
    return token, response.json()


def test_success_payment_confirms_booking(client):
    token, booking = create_booking(client)

    response = client.post(
        "/payments/",
        headers=auth_headers(token),
        json={
            "booking_id": booking["id"],
            "simulate": "SUCCESS",
            "idempotency_key": "payment-key-001",
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "SUCCESS"
    assert response.json()["amount"] == "500.00"

    booking_response = client.get(
        f"/bookings/{booking['id']}",
        headers=auth_headers(token),
    )
    assert booking_response.json()["status"] == "CONFIRMED"


def test_failed_payment_marks_booking_failed(client):
    token, booking = create_booking(client)

    response = client.post(
        "/payments/",
        headers=auth_headers(token),
        json={
            "booking_id": booking["id"],
            "simulate": "FAILED",
            "idempotency_key": "payment-key-002",
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "FAILED"

    booking_response = client.get(
        f"/bookings/{booking['id']}",
        headers=auth_headers(token),
    )
    assert booking_response.json()["status"] == "FAILED"


def test_payment_idempotency(client):
    token, booking = create_booking(client)

    payload = {
        "booking_id": booking["id"],
        "simulate": "SUCCESS",
        "idempotency_key": "same-payment-key",
    }

    first = client.post("/payments/", headers=auth_headers(token), json=payload)
    second = client.post("/payments/", headers=auth_headers(token), json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["provider_payment_id"] == second.json()["provider_payment_id"]


def test_payment_idempotency_different_booking_rejected(client):
    token, booking1 = create_booking(client)
    res1 = client.post(
        "/payments/",
        headers=auth_headers(token),
        json={"booking_id": booking1["id"], "simulate": "SUCCESS", "idempotency_key": "shared-key"},
    )
    assert res1.status_code == 201

    # Create second booking
    res_b2 = client.post(
        "/bookings",
        headers=auth_headers(token),
        json={
            "test_id": booking1["test_id"],
            "centre_id": booking1["centre_id"],
            "appointment_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        },
    )
    booking2 = res_b2.json()

    # Attempt to use same idempotency key for booking 2
    res2 = client.post(
        "/payments/",
        headers=auth_headers(token),
        json={"booking_id": booking2["id"], "simulate": "SUCCESS", "idempotency_key": "shared-key"},
    )
    assert res2.status_code == 409
    assert "belongs to another booking" in res2.json()["detail"].lower()


def test_cannot_pay_already_confirmed_booking(client):
    token, booking = create_booking(client)
    res = client.post(
        "/payments/",
        headers=auth_headers(token),
        json={"booking_id": booking["id"], "simulate": "SUCCESS", "idempotency_key": "key-alpha"},
    )
    assert res.status_code == 201

    # Re-attempt with a DIFFERENT idempotency key
    res2 = client.post(
        "/payments/",
        headers=auth_headers(token),
        json={"booking_id": booking["id"], "simulate": "SUCCESS", "idempotency_key": "key-beta"},
    )
    assert res2.status_code == 409


def test_non_owner_cannot_pay_for_booking(client):
    token, booking = create_booking(client)

    signup(client, email="other@example.com")
    token_other = login(client, email="other@example.com")

    res = client.post(
        "/payments/",
        headers=auth_headers(token_other),
        json={"booking_id": booking["id"], "simulate": "SUCCESS", "idempotency_key": "other-key"},
    )
    assert res.status_code == 403


def test_header_idempotency_key(client):
    token, booking = create_booking(client)
    headers = auth_headers(token)
    headers["Idempotency-Key"] = "header-idempotency-key-001"

    res = client.post(
        "/payments",
        headers=headers,
        json={"booking_id": booking["id"], "simulate": "SUCCESS"},
    )
    assert res.status_code == 201
    assert res.json()["status"] == "SUCCESS"


def test_webhook_is_idempotent(client):
    token, booking = create_booking(client)

    payment = client.post(
        "/payments/",
        headers=auth_headers(token),
        json={
            "booking_id": booking["id"],
            "simulate": "SUCCESS",
            "idempotency_key": "webhook-payment-key",
        },
    ).json()

    payload = {
        "event_id": "evt-12345",
        "provider_payment_id": payment["provider_payment_id"],
        "status": "SUCCESS",
    }

    first = client.post("/payments/webhook/", json=payload)
    second = client.post("/payments/webhook/", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    booking_response = client.get(
        f"/bookings/{booking['id']}",
        headers=auth_headers(token),
    )
    assert booking_response.json()["status"] == "CONFIRMED"


def test_unknown_payment_webhook_is_rejected(client):
    response = client.post(
        "/payments/webhook/",
        json={
            "event_id": "evt-unknown",
            "provider_payment_id": "pay-does-not-exist",
            "status": "SUCCESS",
        },
    )
    assert response.status_code == 404


def test_webhook_cannot_corrupt_confirmed_booking_to_failed(client):
    token, booking = create_booking(client)
    payment = client.post(
        "/payments/",
        headers=auth_headers(token),
        json={"booking_id": booking["id"], "simulate": "SUCCESS", "idempotency_key": "confirmed-key"},
    ).json()

    # Webhook tries to mark confirmed payment as FAILED
    res = client.post(
        "/payments/webhook/",
        json={
            "event_id": "evt-corrupt-attempt",
            "provider_payment_id": payment["provider_payment_id"],
            "status": "FAILED",
        },
    )
    assert res.status_code == 409


def test_cancelled_booking_cannot_be_paid(client):
    token, booking = create_booking(client)

    cancel = client.post(
        f"/bookings/{booking['id']}/cancel",
        headers=auth_headers(token),
    )
    assert cancel.status_code == 200

    payment = client.post(
        "/payments/",
        headers=auth_headers(token),
        json={
            "booking_id": booking["id"],
            "simulate": "SUCCESS",
            "idempotency_key": "cancelled-booking-payment",
        },
    )
    assert payment.status_code == 409


def test_get_payment_for_booking(client):
    token, booking = create_booking(client)
    pay_res = client.post(
        "/payments/",
        headers=auth_headers(token),
        json={"booking_id": booking["id"], "simulate": "SUCCESS", "idempotency_key": "get-pay-key"},
    )
    payment_id = pay_res.json()["id"]

    res = client.get(f"/payments/booking/{booking['id']}", headers=auth_headers(token))
    assert res.status_code == 200
    assert res.json()["id"] == payment_id


def test_webhook_audit_events_endpoint(client):
    admin_token = login_admin(client)
    res = client.get("/payments/webhook/events", headers=auth_headers(admin_token))
    assert res.status_code == 200
    assert isinstance(res.json(), list)
