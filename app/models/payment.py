import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_id = Column(String(36), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), default=PaymentStatus.PENDING.value, nullable=False, index=True)
    payment_method = Column(String(50), default="SIMULATED", nullable=False)
    transaction_ref = Column(String(100), unique=True, index=True, nullable=False)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=True)
    provider_response = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    booking = relationship("Booking", back_populates="payments")
