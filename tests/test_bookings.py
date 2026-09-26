import pytest
from datetime import datetime, timedelta, timezone
from fastapi import status


def test_create_booking_success(client, patient_auth_headers, seed_centre_and_test):
    """Patient books a diagnostic test successfully."""
    centre, test, _ = seed_centre_and_test
    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    payload = {
        "centre_id": centre.id,
        "test_id": test.id,
        "appointment_time": future_time,
        "notes": "Fasting sample required"
    }

    response = client.post("/api/v1/bookings/", json=payload, headers=patient_auth_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == "PENDING"
    assert float(data["amount"]) == 499.00
    assert data["centre_id"] == centre.id
    assert data["test_id"] == test.id


def test_create_booking_past_date_rejected(client, patient_auth_headers, seed_centre_and_test):
    """Booking for a date in the past is rejected."""
    centre, test, _ = seed_centre_and_test
    past_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    payload = {
        "centre_id": centre.id,
        "test_id": test.id,
        "appointment_time": past_time
    }

    response = client.post("/api/v1/bookings/", json=payload, headers=patient_auth_headers)
    assert response.status_code in (status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_400_BAD_REQUEST)


def test_create_booking_test_not_offered(client, patient_auth_headers, admin_auth_headers, seed_centre_and_test):
    """Attempting to book a test not offered by the centre returns 400."""
    centre, _, _ = seed_centre_and_test

    # Create unlinked test
    t_res = client.post(
        "/api/v1/tests/",
        json={"name": "MRI Brain", "code": "MRI-01", "category": "RADIOLOGY"},
        headers=admin_auth_headers
    )
    unlinked_test_id = t_res.json()["id"]

    future_time = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    payload = {
        "centre_id": centre.id,
        "test_id": unlinked_test_id,
        "appointment_time": future_time
    }

    response = client.post("/api/v1/bookings/", json=payload, headers=patient_auth_headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error_code"] == "TEST_NOT_AVAILABLE_AT_CENTRE"


def test_booking_ownership_protection(
    client,
    patient_auth_headers,
    other_auth_headers,
    admin_auth_headers,
    seed_centre_and_test
):
    """Test that patient B cannot view or cancel patient A's booking (403), but admin can."""
    centre, test, _ = seed_centre_and_test
    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # Patient A creates booking
    create_res = client.post(
        "/api/v1/bookings/",
        json={"centre_id": centre.id, "test_id": test.id, "appointment_time": future_time},
        headers=patient_auth_headers
    )
    booking_id = create_res.json()["id"]

    # Patient B attempts to fetch Patient A's booking -> 403 Forbidden
    forbidden_res = client.get(f"/api/v1/bookings/{booking_id}", headers=other_auth_headers)
    assert forbidden_res.status_code == status.HTTP_403_FORBIDDEN

    # Patient B attempts to cancel Patient A's booking -> 403 Forbidden
    cancel_forbidden = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=other_auth_headers)
    assert cancel_forbidden.status_code == status.HTTP_403_FORBIDDEN

    # Admin CAN view booking
    admin_res = client.get(f"/api/v1/bookings/{booking_id}", headers=admin_auth_headers)
    assert admin_res.status_code == status.HTTP_200_OK
    assert admin_res.json()["id"] == booking_id


def test_booking_cancellation_lifecycle(client, patient_auth_headers, seed_centre_and_test):
    """Test cancelling an active booking and rejecting repeated cancellation."""
    centre, test, _ = seed_centre_and_test
    future_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    # Create
    create_res = client.post(
        "/api/v1/bookings/",
        json={"centre_id": centre.id, "test_id": test.id, "appointment_time": future_time},
        headers=patient_auth_headers
    )
    booking_id = create_res.json()["id"]

    # Cancel
    cancel_res = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=patient_auth_headers)
    assert cancel_res.status_code == status.HTTP_200_OK
    assert cancel_res.json()["status"] == "CANCELLED"

    # Repeated cancel returns 400
    repeat_res = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=patient_auth_headers)
    assert repeat_res.status_code == status.HTTP_400_BAD_REQUEST
    assert repeat_res.json()["error_code"] == "BOOKING_ALREADY_CANCELLED"
