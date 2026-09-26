import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base


class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    centre_id = Column(String(36), ForeignKey("diagnostic_centres.id", ondelete="RESTRICT"), nullable=False, index=True)
    test_id = Column(String(36), ForeignKey("diagnostic_tests.id", ondelete="RESTRICT"), nullable=False, index=True)
    centre_test_id = Column(String(36), ForeignKey("centre_tests.id", ondelete="RESTRICT"), nullable=False)
    
    appointment_time = Column(DateTime, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), default=BookingStatus.PENDING.value, nullable=False, index=True)
    notes = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="bookings")
    centre = relationship("DiagnosticCentre", back_populates="bookings")
    test = relationship("DiagnosticTest", back_populates="bookings")
    centre_test = relationship("CentreTest", back_populates="bookings")
    payments = relationship("Payment", back_populates="booking", cascade="all, delete-orphan")
