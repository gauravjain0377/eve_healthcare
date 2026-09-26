import logging
from typing import Optional
from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rate_limiter import rate_limit
from app.schemas.payment import (
    PaymentSimulateRequest,
    PaymentResponse,
    WebhookPayload,
    WebhookResponse
)
from app.services.payment_service import payment_service
from app.api.deps import get_current_user
from app.models.user import User

logger = logging.getLogger("eve_healthcare.payments_api")
router = APIRouter()


@router.post(
    "/",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulate payment processing",
    description=(
        "Simulates processing a payment for a booking. "
        "Transitions the booking state to CONFIRMED on SUCCESS, or FAILED on FAILED. "
        "Supports client-supplied idempotency_key to prevent duplicate transactions."
    )
)
def simulate_payment(
    payment_in: PaymentSimulateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _ = Depends(rate_limit(max_requests=30, window_seconds=60))
):
    payment = payment_service.simulate_payment(db, payment_in, current_user)
    return payment


@router.post(
    "/webhook",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Payment provider webhook (Idempotent)",
    description=(
        "Receives payment-status updates from a payment gateway. "
        "STRICT IDEMPOTENCY: Repeated events with the same event_id are safely ignored "
        "and will not result in duplicate payments or corrupted booking states."
    )
)
def payment_webhook(
    webhook_in: WebhookPayload,
    x_webhook_signature: Optional[str] = Header(None, description="Simulated gateway signature"),
    db: Session = Depends(get_db)
):
    logger.info(f"Webhook received for event_id: {webhook_in.event_id}, type: {webhook_in.event_type}")
    response = payment_service.process_webhook(db, webhook_in)
    return response


@router.post(
    "/webhook/",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
def payment_webhook_slash(
    webhook_in: WebhookPayload,
    x_webhook_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    return payment_service.process_webhook(db, webhook_in)
