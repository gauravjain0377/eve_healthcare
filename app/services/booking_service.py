from typing import Optional, List, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.booking import Booking, BookingStatus
from app.models.centre import DiagnosticCentre
from app.models.test import DiagnosticTest
from app.models.centre_test import CentreTest
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingDetailResponse
from app.core.exceptions import NotFoundException, BadRequestException, ForbiddenException


class BookingService:
    @staticmethod
    def create_booking(db: Session, user: User, booking_in: BookingCreate) -> Booking:
        """Create a new booking in PENDING state."""
        # 1. Verify centre exists & active
        centre = db.query(DiagnosticCentre).filter(
            DiagnosticCentre.id == booking_in.centre_id,
            DiagnosticCentre.is_active == True
        ).first()
        if not centre:
            raise NotFoundException(resource="DiagnosticCentre", identifier=booking_in.centre_id)

        # 2. Verify test exists
        test = db.query(DiagnosticTest).filter(DiagnosticTest.id == booking_in.test_id).first()
        if not test:
            raise NotFoundException(resource="DiagnosticTest", identifier=booking_in.test_id)

        # 3. Verify centre offers this test and it is available
        centre_test = db.query(CentreTest).filter(
            CentreTest.centre_id == booking_in.centre_id,
            CentreTest.test_id == booking_in.test_id,
            CentreTest.is_available == True
        ).first()
        if not centre_test:
            raise BadRequestException(
                detail=f"Test '{test.name}' is not currently available at centre '{centre.name}'.",
                error_code="TEST_NOT_AVAILABLE_AT_CENTRE"
            )

        # 4. Verify appointment date is in future
        now = datetime.now(timezone.utc)
        app_time = booking_in.appointment_time
        if app_time.tzinfo is None:
            app_time = app_time.replace(tzinfo=timezone.utc)
        if app_time <= now:
            raise BadRequestException(
                detail="Appointment time must be in the future.",
                error_code="PAST_APPOINTMENT_TIME"
            )

        # 5. Create booking with authoritative price from CentreTest
        booking = Booking(
            user_id=user.id,
            centre_id=booking_in.centre_id,
            test_id=booking_in.test_id,
            centre_test_id=centre_test.id,
            appointment_time=booking_in.appointment_time,
            amount=centre_test.price,
            status=BookingStatus.PENDING.value,
            notes=booking_in.notes
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        return booking

    @staticmethod
    def get_booking_by_id(db: Session, booking_id: str, current_user: User) -> Booking:
        """Retrieve booking and enforce ownership/authorization."""
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise NotFoundException(resource="Booking", identifier=booking_id)

        # Authorization: regular users can only access their own bookings
        if current_user.role != "ADMIN" and booking.user_id != current_user.id:
            raise ForbiddenException(detail="You are not authorized to view this booking.")

        return booking

    @staticmethod
    def get_booking_detail(db: Session, booking: Booking) -> BookingDetailResponse:
        """Construct a detailed booking response."""
        centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.id == booking.centre_id).first()
        test = db.query(DiagnosticTest).filter(DiagnosticTest.id == booking.test_id).first()
        user = db.query(User).filter(User.id == booking.user_id).first()

        return BookingDetailResponse(
            id=booking.id,
            user_id=booking.user_id,
            centre_id=booking.centre_id,
            test_id=booking.test_id,
            appointment_time=booking.appointment_time,
            amount=booking.amount,
            status=BookingStatus(booking.status),
            notes=booking.notes,
            created_at=booking.created_at,
            updated_at=booking.updated_at,
            centre_name=centre.name if centre else None,
            centre_city=centre.city if centre else None,
            test_name=test.name if test else None,
            test_code=test.code if test else None,
            patient_name=user.full_name if user else None,
            patient_email=user.email if user else None
        )

    @staticmethod
    def get_user_bookings(
        db: Session,
        user: User,
        status: Optional[BookingStatus] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[List[Booking], int]:
        """List bookings. Regular users see only their own; admins see all."""
        query = db.query(Booking)
        if user.role != "ADMIN":
            query = query.filter(Booking.user_id == user.id)

        if status:
            query = query.filter(Booking.status == status.value)

        query = query.order_by(Booking.created_at.desc())
        total = query.count()
        offset = (page - 1) * page_size
        bookings = query.offset(offset).limit(page_size).all()
        return bookings, total

    @staticmethod
    def cancel_booking(db: Session, booking_id: str, current_user: User) -> Booking:
        """Cancel a pending or confirmed booking."""
        booking = BookingService.get_booking_by_id(db, booking_id, current_user)

        if booking.status == BookingStatus.CANCELLED.value:
            raise BadRequestException(
                detail="Booking is already cancelled.",
                error_code="BOOKING_ALREADY_CANCELLED"
            )

        if booking.status == BookingStatus.FAILED.value:
            raise BadRequestException(
                detail="Cannot cancel a failed booking.",
                error_code="CANNOT_CANCEL_FAILED_BOOKING"
            )

        booking.status = BookingStatus.CANCELLED.value
        db.commit()
        db.refresh(booking)
        return booking


booking_service = BookingService()
