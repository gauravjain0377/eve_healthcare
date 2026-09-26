from typing import Optional, List
from math import ceil
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.centre import (
    CentreCreate,
    CentreUpdate,
    CentreResponse,
    CentreDetailResponse,
    CentreTestAssociation,
    CentreTestResponse
)
from app.schemas.common import PaginatedResponse
from app.services.centre_service import centre_service
from app.api.deps import get_current_user, get_current_admin
from app.models.user import User

router = APIRouter()


@router.get(
    "/",
    response_model=PaginatedResponse[CentreResponse],
    summary="List diagnostic centres",
    description="Retrieve diagnostic centres with optional city filtering and pagination."
)
def list_centres(
    city: Optional[str] = Query(None, description="Filter by city name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    centres, total = centre_service.get_centres(db, city=city, page=page, page_size=page_size)
    total_pages = ceil(total / page_size) if total > 0 else 1
    return PaginatedResponse(
        items=centres,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post(
    "/",
    response_model=CentreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a diagnostic centre",
    description="Adds a new diagnostic centre to the platform."
)
def create_centre(
    centre_in: CentreCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_admin)
):
    return centre_service.create_centre(db, centre_in)


@router.get(
    "/{centre_id}",
    response_model=CentreDetailResponse,
    summary="Get centre details with available tests",
    description="Retrieves a diagnostic centre along with all tests offered and their prices."
)
def get_centre(centre_id: str, db: Session = Depends(get_db)):
    centre = centre_service.get_centre_by_id(db, centre_id)
    tests = centre_service.get_centre_tests(db, centre_id)
    
    return CentreDetailResponse(
        id=centre.id,
        name=centre.name,
        address=centre.address,
        city=centre.city,
        contact_phone=centre.contact_phone,
        is_active=centre.is_active,
        created_at=centre.created_at,
        available_tests=tests
    )


@router.put(
    "/{centre_id}",
    response_model=CentreResponse,
    summary="Update diagnostic centre",
    description="Update metadata or active status for a diagnostic centre."
)
def update_centre(
    centre_id: str,
    centre_in: CentreUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_admin)
):
    return centre_service.update_centre(db, centre_id, centre_in)


@router.post(
    "/{centre_id}/tests",
    summary="Associate test with centre and configure pricing",
    description="Add or update a diagnostic test offered by this centre with custom pricing."
)
def add_test_to_centre(
    centre_id: str,
    association: CentreTestAssociation,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_admin)
):
    centre_test = centre_service.add_test_to_centre(db, centre_id, association)
    return {
        "message": "Test pricing configured successfully for centre.",
        "centre_id": centre_test.centre_id,
        "test_id": centre_test.test_id,
        "price": str(centre_test.price),
        "turnaround_hours": centre_test.turnaround_hours,
        "is_available": centre_test.is_available
    }


@router.get(
    "/{centre_id}/tests",
    response_model=List[CentreTestResponse],
    summary="List tests offered by a centre",
    description="Retrieve all diagnostic tests offered by the specified centre with pricing."
)
def get_centre_tests(centre_id: str, db: Session = Depends(get_db)):
    return centre_service.get_centre_tests(db, centre_id)
