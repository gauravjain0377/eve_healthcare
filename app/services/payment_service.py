import json
import logging
import uuid
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.booking import Booking, BookingStatus
from app.models.payment import Payment, PaymentStatus
from app.models.webhook_event import WebhookEvent
from app.models.user import User
from app.schemas.payment import (
    PaymentSimulateRequest,
    WebhookPayload,
    WebhookResponse,
)
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    ForbiddenException,
    ConflictException,
)

logger = logging.getLogger("eve_healthcare.payments")


class PaymentService:
    @staticmethod
    def simulate_payment(
        db: Session,
        payment_in: PaymentSimulateRequest,
        current_user: User
    ) -> Payment:
        """
        Simulate payment processing for a booking.
        Updates booking to CONFIRMED on SUCCESS, or FAILED on FAILED.
        Respects idempotency key if provided.
        """
        # 1. Check idempotency key if provided
        if payment_in.idempotency_key:
            existing_payment = db.query(Payment).filter(
                Payment.idempotency_key == payment_in.idempotency_key
            ).first()
            if existing_payment:
                logger.info(f"Idempotent payment replay detected for key: {payment_in.idempotency_key}")
                return existing_payment

        # 2. Retrieve booking & check authorization
        booking = db.query(Booking).filter(Booking.id == payment_in.booking_id).first()
        if not booking:
            raise NotFoundException(resource="Booking", identifier=payment_in.booking_id)

        if current_user.role != "ADMIN" and booking.user_id != current_user.id:
            raise ForbiddenException(detail="You are not authorized to pay for this booking.")

        # 3. Validate booking status before payment
        if booking.status == BookingStatus.CONFIRMED.value:
            raise BadRequestException(
                detail="Booking is already confirmed and paid for.",
                error_code="BOOKING_ALREADY_PAID"
            )

        if booking.status == BookingStatus.CANCELLED.value:
            raise BadRequestException(
                detail="Cannot make payment for a cancelled booking.",
                error_code="CANNOT_PAY_CANCELLED_BOOKING"
            )

        # 4. Determine simulation outcome
        status_outcome = payment_in.force_status or PaymentStatus.SUCCESS
        transaction_ref = f"txn_sim_{uuid.uuid4().hex[:12]}"

        # 5. Atomic state update
        payment = Payment(
            booking_id=booking.id,
            amount=booking.amount,
            status=status_outcome.value,
            payment_method=payment_in.payment_method,
            transaction_ref=transaction_ref,
            idempotency_key=payment_in.idempotency_key,
            provider_response=json.dumps({
                "simulation": True,
                "outcome": status_outcome.value,
                "notes": "Simulated payment transaction"
            })
        )
        db.add(payment)

        if status_outcome == PaymentStatus.SUCCESS:
            booking.status = BookingStatus.CONFIRMED.value
        else:
            booking.status = BookingStatus.FAILED.value

        try:
            db.commit()
            db.refresh(payment)
            db.refresh(booking)
        except IntegrityError:
            db.rollback()
            if payment_in.idempotency_key:
                existing = db.query(Payment).filter(
                    Payment.idempotency_key == payment_in.idempotency_key
                ).first()
                if existing:
                    return existing
            raise ConflictException(detail="Payment conflict or concurrent payment detected.")

        return payment

    @staticmethod
    def process_webhook(db: Session, webhook_in: WebhookPayload) -> WebhookResponse:
        """
        Process payment provider webhook in a strictly idempotent manner.
        If an event with the same event_id was already processed, returns 200 OK
        with 'duplicate_ignored' without re-running payment logic or modifying state.
        """
        event_id = webhook_in.event_id
        event_data = webhook_in.data

        # 1. Idempotency Check: Query for existing webhook event record
        existing_event = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()
        if existing_event:
            logger.info(f"Duplicate webhook event ignored: {event_id}")
            # Fetch current booking status to return in response
            booking = db.query(Booking).filter(Booking.id == existing_event.booking_id).first()
            return WebhookResponse(
                status="duplicate_ignored",
                event_id=event_id,
                booking_id=existing_event.booking_id,
                booking_status=booking.status if booking else None,
                message="Duplicate webhook event received. No action taken."
            )

        # 2. Check if referenced booking exists
        booking = db.query(Booking).filter(Booking.id == event_data.booking_id).first()
        if not booking:
            # Record failed event for audit trail
            failed_event = WebhookEvent(
                event_id=event_id,
                event_type=webhook_in.event_type,
                booking_id=event_data.booking_id,
                status="FAILED",
                payload=webhook_in.model_dump_json(),
                error_message=f"Booking '{event_data.booking_id}' not found."
            )
            db.add(failed_event)
            db.commit()
            raise NotFoundException(resource="Booking", identifier=event_data.booking_id)

        # 3. Create WebhookEvent audit entry
        webhook_record = WebhookEvent(
            event_id=event_id,
            event_type=webhook_in.event_type,
            booking_id=booking.id,
            status="PROCESSED",
            payload=webhook_in.model_dump_json()
        )
        db.add(webhook_record)

        # 4. Check if transaction ref already exists in payments (avoid duplicate payment rows)
        existing_payment = db.query(Payment).filter(
            Payment.transaction_ref == event_data.transaction_ref
        ).first()

        if not existing_payment:
            payment = Payment(
                booking_id=booking.id,
                amount=event_data.amount,
                status=event_data.status.value,
                payment_method=event_data.payment_method or "WEBHOOK",
                transaction_ref=event_data.transaction_ref,
                provider_response=webhook_in.model_dump_json()
            )
            db.add(payment)

        # 5. Transition booking state according to payment status
        if event_data.status == PaymentStatus.SUCCESS:
            # Only update if not already cancelled
            if booking.status != BookingStatus.CANCELLED.value:
                booking.status = BookingStatus.CONFIRMED.value
        elif event_data.status == PaymentStatus.FAILED:
            if booking.status == BookingStatus.PENDING.value:
                booking.status = BookingStatus.FAILED.value

        try:
            db.commit()
            db.refresh(booking)
        except IntegrityError as e:
            db.rollback()
            # In case of concurrent delivery of the identical event
            existing = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()
            if existing:
                return WebhookResponse(
                    status="duplicate_ignored",
                    event_id=event_id,
                    booking_id=booking.id,
                    booking_status=booking.status,
                    message="Concurrent duplicate webhook resolved safely."
                )
            raise BadRequestException(detail=f"Database integrity error during webhook processing: {str(e)}")

        return WebhookResponse(
            status="processed",
            event_id=event_id,
            booking_id=booking.id,
            booking_status=booking.status,
            message=f"Webhook processed successfully. Booking status updated to {booking.status}."
        )


payment_service = PaymentService()
