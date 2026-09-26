from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.booking import (
    BookingCreate,
    BookingResponse,
    BookingDetailResponse
)
from app.schemas.common import PaginatedResponse
from app.models.booking import BookingStatus
from app.models.user import User
from app.services.booking_service import booking_service
from app.api.deps import get_current_user

router = APIRouter()


@router.post(
    "/",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Book a diagnostic test",
    description="Allows an authenticated patient to book a diagnostic test at a selected centre."
)
def create_booking(
    booking_in: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return booking_service.create_booking(db, current_user, booking_in)


@router.get(
    "/",
    response_model=PaginatedResponse[BookingResponse],
    summary="List bookings",
    description="Retrieve bookings. Patients see their own; administrators see all bookings."
)
def list_bookings(
    status: Optional[BookingStatus] = Query(None, description="Filter by booking status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    bookings, total = booking_service.get_user_bookings(
        db, current_user, status=status, page=page, page_size=page_size
    )
    total_pages = ceil(total / page_size) if total > 0 else 1
    return PaginatedResponse(
        items=bookings,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get(
    "/{booking_id}",
    response_model=BookingDetailResponse,
    summary="Get booking details",
    description="Retrieve full details for a specific booking. Restricted to booking owner or admin."
)
def get_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = booking_service.get_booking_by_id(db, booking_id, current_user)
    return booking_service.get_booking_detail(db, booking)


@router.post(
    "/{booking_id}/cancel",
    response_model=BookingResponse,
    summary="Cancel a booking",
    description="Allows a user or admin to cancel an active booking in PENDING or CONFIRMED state."
)
def cancel_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return booking_service.cancel_booking(db, booking_id, current_user)
