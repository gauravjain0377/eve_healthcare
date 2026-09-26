from typing import Optional, List, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.centre import DiagnosticCentre
from app.models.test import DiagnosticTest
from app.models.centre_test import CentreTest
from app.schemas.centre import CentreCreate, CentreUpdate, CentreTestAssociation
from app.schemas.test import TestCreate, TestUpdate
from app.core.exceptions import NotFoundException, ConflictException, BadRequestException
from app.core.cache import cache


class CentreService:
    CACHE_PREFIX_CENTRES = "centres:"
    CACHE_PREFIX_TESTS = "tests:"

    # --- Centres ---

    @staticmethod
    def get_centres(
        db: Session,
        city: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[List[DiagnosticCentre], int]:
        cache_key = f"{CentreService.CACHE_PREFIX_CENTRES}list:city={city}:p={page}:s={page_size}"
        cached = cache.get(cache_key)
        # Note: if cached, we can return or read directly. Here we query DB to guarantee fresh data or caching serialized
        
        query = db.query(DiagnosticCentre).filter(DiagnosticCentre.is_active == True)
        if city:
            query = query.filter(func.lower(DiagnosticCentre.city) == city.lower())
        
        total = query.count()
        offset = (page - 1) * page_size
        centres = query.offset(offset).limit(page_size).all()
        return centres, total

    @staticmethod
    def get_centre_by_id(db: Session, centre_id: str) -> DiagnosticCentre:
        centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.id == centre_id).first()
        if not centre:
            raise NotFoundException(resource="DiagnosticCentre", identifier=centre_id)
        return centre

    @staticmethod
    def create_centre(db: Session, centre_in: CentreCreate) -> DiagnosticCentre:
        centre = DiagnosticCentre(
            name=centre_in.name,
            address=centre_in.address,
            city=centre_in.city,
            contact_phone=centre_in.contact_phone,
            is_active=True
        )
        db.add(centre)
        db.commit()
        db.refresh(centre)
        cache.invalidate_prefix(CentreService.CACHE_PREFIX_CENTRES)
        return centre

    @staticmethod
    def update_centre(db: Session, centre_id: str, centre_in: CentreUpdate) -> DiagnosticCentre:
        centre = CentreService.get_centre_by_id(db, centre_id)
        update_data = centre_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(centre, field, value)
        db.commit()
        db.refresh(centre)
        cache.invalidate_prefix(CentreService.CACHE_PREFIX_CENTRES)
        return centre

    # --- Tests ---

    @staticmethod
    def get_tests(
        db: Session,
        category: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[List[DiagnosticTest], int]:
        query = db.query(DiagnosticTest)
        if category:
            query = query.filter(func.lower(DiagnosticTest.category) == category.lower())
        
        total = query.count()
        offset = (page - 1) * page_size
        tests = query.offset(offset).limit(page_size).all()
        return tests, total

    @staticmethod
    def get_test_by_id(db: Session, test_id: str) -> DiagnosticTest:
        test = db.query(DiagnosticTest).filter(DiagnosticTest.id == test_id).first()
        if not test:
            raise NotFoundException(resource="DiagnosticTest", identifier=test_id)
        return test

    @staticmethod
    def create_test(db: Session, test_in: TestCreate) -> DiagnosticTest:
        existing = db.query(DiagnosticTest).filter(DiagnosticTest.code == test_in.code.upper()).first()
        if existing:
            raise ConflictException(
                detail=f"Test with code '{test_in.code}' already exists.",
                error_code="TEST_CODE_ALREADY_EXISTS"
            )
        
        test = DiagnosticTest(
            name=test_in.name,
            code=test_in.code.upper(),
            description=test_in.description,
            category=test_in.category.upper()
        )
        db.add(test)
        db.commit()
        db.refresh(test)
        cache.invalidate_prefix(CentreService.CACHE_PREFIX_TESTS)
        return test

    # --- Centre & Test Relationship ---

    @staticmethod
    def add_test_to_centre(
        db: Session,
        centre_id: str,
        association: CentreTestAssociation
    ) -> CentreTest:
        # Validate centre exists
        CentreService.get_centre_by_id(db, centre_id)
        # Validate test exists
        CentreService.get_test_by_id(db, association.test_id)

        existing = db.query(CentreTest).filter(
            CentreTest.centre_id == centre_id,
            CentreTest.test_id == association.test_id
        ).first()

        if existing:
            existing.price = association.price
            existing.turnaround_hours = association.turnaround_hours
            existing.is_available = association.is_available
            db.commit()
            db.refresh(existing)
            cache.invalidate_prefix(CentreService.CACHE_PREFIX_CENTRES)
            return existing

        centre_test = CentreTest(
            centre_id=centre_id,
            test_id=association.test_id,
            price=association.price,
            turnaround_hours=association.turnaround_hours,
            is_available=association.is_available
        )
        db.add(centre_test)
        db.commit()
        db.refresh(centre_test)
        cache.invalidate_prefix(CentreService.CACHE_PREFIX_CENTRES)
        return centre_test

    @staticmethod
    def get_centre_tests(db: Session, centre_id: str) -> List[dict]:
        """Fetch all tests offered by a centre with pricing."""
        CentreService.get_centre_by_id(db, centre_id)
        
        results = (
            db.query(CentreTest, DiagnosticTest)
            .join(DiagnosticTest, CentreTest.test_id == DiagnosticTest.id)
            .filter(CentreTest.centre_id == centre_id, CentreTest.is_available == True)
            .all()
        )
        
        items = []
        for ct, t in results:
            items.append({
                "centre_test_id": ct.id,
                "test_id": t.id,
                "name": t.name,
                "code": t.code,
                "category": t.category,
                "price": ct.price,
                "turnaround_hours": ct.turnaround_hours,
                "is_available": ct.is_available,
            })
        return items


centre_service = CentreService()
