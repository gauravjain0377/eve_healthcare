import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base


class DiagnosticCentre(Base):
    __tablename__ = "diagnostic_centres"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    address = Column(String(500), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    contact_phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    centre_tests = relationship("CentreTest", back_populates="centre", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="centre")
