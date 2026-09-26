import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base


class DiagnosticTest(Base):
    __tablename__ = "diagnostic_tests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), default="GENERAL", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    centre_tests = relationship("CentreTest", back_populates="test", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="test")
