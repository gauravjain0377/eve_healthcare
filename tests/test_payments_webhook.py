import pytest
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import status


@pytest.fixture
def active_booking(client, patient_auth_headers, seed_centre_and_test) -> str:
    """Fixture that creates a pending booking and returns its ID."""
    centre, test, _ = seed_centre_and_test
    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    res = client.post(
        "/api/v1/bookings/",
        json={"centre_id": centre.id, "test_id": test.id, "appointment_time": future_time},
        headers=patient_auth_headers
    )
    return res.json()["id"]


# --- Simulated Payment Tests ---

def test_simulate_payment_success(client, patient_auth_headers, active_booking):
    """Simulated payment with SUCCESS transitions booking to CONFIRMED."""
    payload = {
        "booking_id": active_booking,
        "payment_method": "SIMULATED_CARD",
        "force_status": "SUCCESS"
    }
    response = client.post("/payments/", json=payload, headers=patient_auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["booking_id"] == active_booking
    assert "transaction_ref" in data

    # Verify booking status transitioned to CONFIRMED
    booking_res = client.get(f"/api/v1/bookings/{active_booking}", headers=patient_auth_headers)
    assert booking_res.json()["status"] == "CONFIRMED"


def test_simulate_payment_failure(client, patient_auth_headers, active_booking):
    """Simulated payment with FAILED transitions booking to FAILED."""
    payload = {
        "booking_id": active_booking,
        "payment_method": "UPI",
        "force_status": "FAILED"
    }
    response = client.post("/payments/", json=payload, headers=patient_auth_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "FAILED"

    # Verify booking status transitioned to FAILED
    booking_res = client.get(f"/api/v1/bookings/{active_booking}", headers=patient_auth_headers)
    assert booking_res.json()["status"] == "FAILED"


def test_payment_on_already_confirmed_booking_rejected(client, patient_auth_headers, active_booking):
    """Cannot pay again for an already CONFIRMED booking."""
    # First payment succeeds
    client.post(
        "/payments/",
        json={"booking_id": active_booking, "force_status": "SUCCESS"},
        headers=patient_auth_headers
    )

    # Second payment attempt must be rejected
    res2 = client.post(
        "/payments/",
        json={"booking_id": active_booking, "force_status": "SUCCESS"},
        headers=patient_auth_headers
    )
    assert res2.status_code == status.HTTP_400_BAD_REQUEST
    assert res2.json()["error_code"] == "BOOKING_ALREADY_PAID"


def test_payment_idempotency_key_replay(client, patient_auth_headers, active_booking):
    """Replaying payment request with the same idempotency_key returns identical transaction without charging twice."""
    key = f"idemp_{uuid.uuid4().hex}"
    payload = {
        "booking_id": active_booking,
        "force_status": "SUCCESS",
        "idempotency_key": key
    }

    res1 = client.post("/payments/", json=payload, headers=patient_auth_headers)
    assert res1.status_code == status.HTTP_200_OK
    data1 = res1.json()

    # Replay identical payment with same idempotency key
    res2 = client.post("/payments/", json=payload, headers=patient_auth_headers)
    assert res2.status_code == status.HTTP_200_OK
    data2 = res2.json()

    # Must return exact same transaction reference
    assert data1["transaction_ref"] == data2["transaction_ref"]
    assert data1["id"] == data2["id"]


# --- Webhook Tests & Strict Idempotency ---

def test_webhook_payment_success(client, patient_auth_headers, active_booking):
    """Payment provider webhook delivers SUCCESS -> booking updated to CONFIRMED."""
    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    webhook_payload = {
        "event_id": event_id,
        "event_type": "payment.succeeded",
        "data": {
            "booking_id": active_booking,
            "amount": 499.00,
            "transaction_ref": f"txn_wh_{uuid.uuid4().hex[:8]}",
            "status": "SUCCESS"
        }
    }

    response = client.post("/payments/webhook/", json=webhook_payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "processed"
    assert data["booking_status"] == "CONFIRMED"

    # Verify booking is now CONFIRMED
    booking_res = client.get(f"/api/v1/bookings/{active_booking}", headers=patient_auth_headers)
    assert booking_res.json()["status"] == "CONFIRMED"


def test_webhook_strict_idempotency(client, patient_auth_headers, active_booking, db):
    """
    CRITICAL REQUIREMENT:
    Sending the same webhook event 3 times must only process once.
    Subsequent calls must return duplicate_ignored and not corrupt data.
    """
    from app.models.payment import Payment
    from app.models.webhook_event import WebhookEvent

    event_id = f"evt_idemp_{uuid.uuid4().hex[:12]}"
    txn_ref = f"txn_wh_{uuid.uuid4().hex[:8]}"

    webhook_payload = {
        "event_id": event_id,
        "event_type": "payment.succeeded",
        "data": {
            "booking_id": active_booking,
            "amount": 499.00,
            "transaction_ref": txn_ref,
            "status": "SUCCESS"
        }
    }

    # 1. First webhook call -> processed
    res1 = client.post("/payments/webhook/", json=webhook_payload)
    assert res1.status_code == status.HTTP_200_OK
    assert res1.json()["status"] == "processed"
    assert res1.json()["booking_status"] == "CONFIRMED"

    # 2. Duplicate webhook call 2 -> duplicate_ignored
    res2 = client.post("/payments/webhook/", json=webhook_payload)
    assert res2.status_code == status.HTTP_200_OK
    assert res2.json()["status"] == "duplicate_ignored"

    # 3. Duplicate webhook call 3 -> duplicate_ignored
    res3 = client.post("/payments/webhook/", json=webhook_payload)
    assert res3.status_code == status.HTTP_200_OK
    assert res3.json()["status"] == "duplicate_ignored"

    # 4. Verify DB state: exactly 1 payment record and 1 webhook event record
    payments_count = db.query(Payment).filter(Payment.transaction_ref == txn_ref).count()
    assert payments_count == 1

    events_count = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).count()
    assert events_count == 1

    # Verify booking remains CONFIRMED without corruption
    booking_res = client.get(f"/api/v1/bookings/{active_booking}", headers=patient_auth_headers)
    assert booking_res.json()["status"] == "CONFIRMED"


def test_webhook_invalid_booking_id(client):
    """Webhook referencing non-existent booking returns 404."""
    fake_booking_id = str(uuid.uuid4())
    webhook_payload = {
        "event_id": f"evt_err_{uuid.uuid4().hex[:8]}",
        "event_type": "payment.succeeded",
        "data": {
            "booking_id": fake_booking_id,
            "amount": 100.00,
            "transaction_ref": "txn_fake_123",
            "status": "SUCCESS"
        }
    }
    response = client.post("/payments/webhook/", json=webhook_payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
