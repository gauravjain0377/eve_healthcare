from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.test import TestCreate, TestUpdate, TestResponse
from app.schemas.common import PaginatedResponse
from app.services.centre_service import centre_service
from app.api.deps import get_current_admin
from app.models.user import User

router = APIRouter()


@router.get(
    "/",
    response_model=PaginatedResponse[TestResponse],
    summary="List diagnostic tests",
    description="Retrieve diagnostic tests catalog with optional category filtering and pagination."
)
def list_tests(
    category: Optional[str] = Query(None, description="Filter by test category"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    tests, total = centre_service.get_tests(db, category=category, page=page, page_size=page_size)
    total_pages = ceil(total / page_size) if total > 0 else 1
    return PaginatedResponse(
        items=tests,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post(
    "/",
    response_model=TestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a diagnostic test",
    description="Adds a new diagnostic test type to the global test catalog."
)
def create_test(
    test_in: TestCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_admin)
):
    return centre_service.create_test(db, test_in)


@router.get(
    "/{test_id}",
    response_model=TestResponse,
    summary="Get diagnostic test details",
    description="Retrieve a single diagnostic test by its ID."
)
def get_test(test_id: str, db: Session = Depends(get_db)):
    return centre_service.get_test_by_id(db, test_id)
