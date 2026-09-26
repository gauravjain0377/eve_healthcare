from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field
from app.models.payment import PaymentStatus


class PaymentSimulateRequest(BaseModel):
    booking_id: str = Field(..., description="ID of the booking to pay for")
    payment_method: str = Field("SIMULATED_CARD", description="Method: SIMULATED_CARD, UPI, NET_BANKING")
    force_status: Optional[PaymentStatus] = Field(
        None,
        description="Optional simulation outcome override: SUCCESS or FAILED (defaults to SUCCESS)"
    )
    idempotency_key: Optional[str] = Field(
        None,
        description="Optional unique key to ensure payment request is processed only once"
    )


class PaymentResponse(BaseModel):
    id: str
    booking_id: str
    amount: Decimal
    status: PaymentStatus
    payment_method: str
    transaction_ref: str
    idempotency_key: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookPaymentData(BaseModel):
    booking_id: str
    amount: Decimal
    transaction_ref: str
    status: PaymentStatus  # SUCCESS or FAILED
    payment_method: Optional[str] = "GATEWAY_WEBHOOK"
    reason: Optional[str] = None


class WebhookPayload(BaseModel):
    event_id: str = Field(..., description="Unique event identifier from payment provider, e.g. evt_93847294")
    event_type: str = Field(..., description="Event type, e.g. payment.succeeded or payment.failed")
    data: WebhookPaymentData = Field(..., description="Payment event payload")
    created_at: Optional[datetime] = None


class WebhookResponse(BaseModel):
    status: str  # "processed", "duplicate_ignored", "failed"
    event_id: str
    booking_id: Optional[str] = None
    booking_status: Optional[str] = None
    message: str
