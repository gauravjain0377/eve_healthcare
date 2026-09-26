"""
Database seeder script for EVE Healthcare.
Pre-populates the database with admin user, test patients, centres, and diagnostic tests.
"""
from decimal import Decimal
from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.centre import DiagnosticCentre
from app.models.test import DiagnosticTest
from app.models.centre_test import CentreTest


def seed():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Admin User
        admin = db.query(User).filter(User.email == "admin@evehealthcare.com").first()
        if not admin:
            admin = User(
                email="admin@evehealthcare.com",
                hashed_password=hash_password("admin123"),
                full_name="Dr. Administrator",
                role="ADMIN",
                is_active=True
            )
            db.add(admin)
            print("[+] Created default admin: admin@evehealthcare.com / admin123")

        # 2. Patient User
        patient = db.query(User).filter(User.email == "patient@example.com").first()
        if not patient:
            patient = User(
                email="patient@example.com",
                hashed_password=hash_password("password123"),
                full_name="John Doe",
                role="PATIENT",
                is_active=True
            )
            db.add(patient)
            print("[+] Created default patient: patient@example.com / password123")

        db.commit()

        # 3. Diagnostic Centres
        centres_data = [
            {
                "name": "Apollo Diagnostics - Indiranagar",
                "address": "100 Feet Road, HAL 2nd Stage, Indiranagar",
                "city": "Bangalore",
                "contact_phone": "+918025201122"
            },
            {
                "name": "SRL Diagnostics - Bandra West",
                "address": "Hill Road, Bandra West",
                "city": "Mumbai",
                "contact_phone": "+912226402233"
            },
            {
                "name": "Max Lab - Connaught Place",
                "address": "Barakhamba Road, Connaught Place",
                "city": "Delhi",
                "contact_phone": "+911143501234"
            }
        ]

        created_centres = []
        for c in centres_data:
            existing = db.query(DiagnosticCentre).filter(DiagnosticCentre.name == c["name"]).first()
            if not existing:
                centre = DiagnosticCentre(**c)
                db.add(centre)
                db.commit()
                db.refresh(centre)
                created_centres.append(centre)
                print(f"[+] Created Centre: {centre.name}")
            else:
                created_centres.append(existing)

        # 4. Diagnostic Tests
        tests_data = [
            {
                "name": "Complete Blood Count (CBC)",
                "code": "CBC-001",
                "description": "Measures red/white blood cells, hemoglobin, and platelets.",
                "category": "HEMATOLOGY"
            },
            {
                "name": "Lipid Profile",
                "code": "LIPID-002",
                "description": "Measures total cholesterol, HDL, LDL, and triglycerides.",
                "category": "BIOCHEMISTRY"
            },
            {
                "name": "Thyroid Stimulating Hormone (TSH)",
                "code": "THY-003",
                "description": "Evaluates thyroid gland function.",
                "category": "ENDOCRINOLOGY"
            },
            {
                "name": "HbA1c (Glycated Hemoglobin)",
                "code": "DIAB-004",
                "description": "Assesses 3-month average blood glucose control.",
                "category": "DIABETES"
            }
        ]

        created_tests = []
        for t in tests_data:
            existing = db.query(DiagnosticTest).filter(DiagnosticTest.code == t["code"]).first()
            if not existing:
                test = DiagnosticTest(**t)
                db.add(test)
                db.commit()
                db.refresh(test)
                created_tests.append(test)
                print(f"[+] Created Test: {test.name}")
            else:
                created_tests.append(existing)

        # 5. Link Tests to Centres with Pricing
        prices = [
            (Decimal("450.00"), 12),
            (Decimal("750.00"), 24),
            (Decimal("550.00"), 24),
            (Decimal("600.00"), 12),
        ]

        for centre in created_centres:
            for i, test in enumerate(created_tests):
                existing_link = db.query(CentreTest).filter(
                    CentreTest.centre_id == centre.id,
                    CentreTest.test_id == test.id
                ).first()
                if not existing_link:
                    price, turnaround = prices[i % len(prices)]
                    link = CentreTest(
                        centre_id=centre.id,
                        test_id=test.id,
                        price=price,
                        turnaround_hours=turnaround,
                        is_available=True
                    )
                    db.add(link)
        db.commit()
        print("[+] All centres linked with diagnostic tests and prices successfully.")
        print("\nSeed completed successfully!")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
