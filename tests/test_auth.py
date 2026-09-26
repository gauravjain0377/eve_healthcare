import pytest
from fastapi import status


def test_user_signup_success(client):
    """Test successful user registration."""
    payload = {
        "email": "newpatient@example.com",
        "password": "securepassword123",
        "full_name": "Alice Wonderland",
        "role": "PATIENT"
    }
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "newpatient@example.com"
    assert data["full_name"] == "Alice Wonderland"
    assert data["role"] == "PATIENT"
    assert "id" in data
    assert "hashed_password" not in data


def test_user_signup_duplicate_email(client, patient_user):
    """Test signup with duplicate email returns 409 Conflict."""
    payload = {
        "email": patient_user.email,
        "password": "anotherpassword",
        "full_name": "Duplicate User",
        "role": "PATIENT"
    }
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["error_code"] == "EMAIL_ALREADY_REGISTERED"


def test_user_signup_short_password(client):
    """Test validation error when password is under 6 characters."""
    payload = {
        "email": "short@example.com",
        "password": "123",
        "full_name": "Short Pass"
    }
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_user_login_success(client, patient_user):
    """Test successful login returns valid JWT Bearer token."""
    payload = {
        "email": "patient@example.com",
        "password": "password123"
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "patient@example.com"


def test_user_login_invalid_credentials(client, patient_user):
    """Test login with wrong password returns 401."""
    payload = {
        "email": "patient@example.com",
        "password": "wrongpassword"
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_me_authenticated(client, patient_auth_headers):
    """Test /me returns profile for authenticated user."""
    response = client.get("/api/v1/auth/me", headers=patient_auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "patient@example.com"


def test_get_me_unauthenticated(client):
    """Test /me rejects unauthenticated request with 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
