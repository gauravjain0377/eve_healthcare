import pytest
from fastapi import status


def test_create_centre_as_admin(client, admin_auth_headers):
    """Admin can create a diagnostic centre."""
    payload = {
        "name": "Manipal Diagnostics",
        "address": "98 HAL Old Airport Rd",
        "city": "Bangalore",
        "contact_phone": "+918025024444"
    }
    response = client.post("/api/v1/centres/", json=payload, headers=admin_auth_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Manipal Diagnostics"
    assert data["city"] == "Bangalore"
    assert data["is_active"] is True


def test_create_centre_as_patient_forbidden(client, patient_auth_headers):
    """Patient cannot create diagnostic centres (403)."""
    payload = {
        "name": "Unauthorized Centre",
        "address": "Some Street",
        "city": "Delhi"
    }
    response = client.post("/api/v1/centres/", json=payload, headers=patient_auth_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_list_centres_with_city_filter(client, seed_centre_and_test):
    """Test listing centres and filtering by city."""
    centre, _, _ = seed_centre_and_test
    
    # Matching city
    response = client.get("/api/v1/centres/?city=Bangalore")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] >= 1
    assert data["items"][0]["city"] == "Bangalore"

    # Non-matching city
    response_none = client.get("/api/v1/centres/?city=Mumbai")
    assert response_none.status_code == status.HTTP_200_OK
    assert response_none.json()["total"] == 0


def test_create_test_and_associate_with_centre(client, admin_auth_headers, seed_centre_and_test):
    """Admin creates diagnostic test and associates with centre with custom pricing."""
    centre, _, _ = seed_centre_and_test

    # 1. Create a new test
    test_payload = {
        "name": "Lipid Profile Panel",
        "code": "LIPID-01",
        "description": "Cholesterol and triglyceride assessment",
        "category": "BIOCHEMISTRY"
    }
    t_res = client.post("/api/v1/tests/", json=test_payload, headers=admin_auth_headers)
    assert t_res.status_code == status.HTTP_201_CREATED
    test_id = t_res.json()["id"]

    # 2. Associate with centre with price
    assoc_payload = {
        "test_id": test_id,
        "price": 850.50,
        "turnaround_hours": 24,
        "is_available": True
    }
    a_res = client.post(f"/api/v1/centres/{centre.id}/tests", json=assoc_payload, headers=admin_auth_headers)
    assert a_res.status_code == status.HTTP_200_OK

    # 3. Retrieve centre details with tests
    c_res = client.get(f"/api/v1/centres/{centre.id}")
    assert c_res.status_code == status.HTTP_200_OK
    c_data = c_res.json()
    assert len(c_data["available_tests"]) == 2
    test_codes = [t["code"] for t in c_data["available_tests"]]
    assert "LIPID-01" in test_codes
    assert "CBC-001" in test_codes
