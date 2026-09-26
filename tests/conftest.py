import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.security import hash_password, create_access_token
from app.models.user import User
from app.models.centre import DiagnosticCentre
from app.models.test import DiagnosticTest
from app.models.centre_test import CentreTest
from app.models.booking import Booking, BookingStatus

# Use an in-memory SQLite database for fast, isolated tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create fresh tables for every test function and drop afterward."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """TestClient that overrides the get_db dependency to use the test database."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def patient_user(db) -> User:
    """Create a sample patient user."""
    user = User(
        email="patient@example.com",
        hashed_password=hash_password("password123"),
        full_name="Jane Doe",
        role="PATIENT",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def other_patient_user(db) -> User:
    """Create a second patient user to test ownership boundaries."""
    user = User(
        email="other@example.com",
        hashed_password=hash_password("password123"),
        full_name="John Smith",
        role="PATIENT",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db) -> User:
    """Create a sample admin user."""
    admin = User(
        email="admin@evehealthcare.com",
        hashed_password=hash_password("adminpass123"),
        full_name="Admin Supervisor",
        role="ADMIN",
        is_active=True
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def patient_auth_headers(patient_user) -> dict:
    """Bearer token headers for patient."""
    token = create_access_token(patient_user.id, extra_claims={"role": patient_user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(other_patient_user) -> dict:
    """Bearer token headers for second patient."""
    token = create_access_token(other_patient_user.id, extra_claims={"role": other_patient_user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(admin_user) -> dict:
    """Bearer token headers for admin."""
    token = create_access_token(admin_user.id, extra_claims={"role": admin_user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seed_centre_and_test(db):
    """Seed a centre and a test with pricing."""
    centre = DiagnosticCentre(
        name="Apollo Diagnostics Indiranagar",
        address="100 Feet Rd, Indiranagar",
        city="Bangalore",
        contact_phone="+919876543210",
        is_active=True
    )
    db.add(centre)

    test = DiagnosticTest(
        name="Complete Blood Count (CBC)",
        code="CBC-001",
        description="Comprehensive evaluation of overall health",
        category="HEMATOLOGY"
    )
    db.add(test)
    db.commit()

    centre_test = CentreTest(
        centre_id=centre.id,
        test_id=test.id,
        price=Decimal("499.00"),
        turnaround_hours=12,
        is_available=True
    )
    db.add(centre_test)
    db.commit()

    return centre, test, centre_test
