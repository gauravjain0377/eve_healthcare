import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class CentreTest(Base):
    __tablename__ = "centre_tests"
    __table_args__ = (
        UniqueConstraint("centre_id", "test_id", name="uq_centre_test"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    centre_id = Column(String(36), ForeignKey("diagnostic_centres.id", ondelete="CASCADE"), nullable=False)
    test_id = Column(String(36), ForeignKey("diagnostic_tests.id", ondelete="CASCADE"), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    turnaround_hours = Column(Integer, default=24, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    centre = relationship("DiagnosticCentre", back_populates="centre_tests")
    test = relationship("DiagnosticTest", back_populates="centre_tests")
    bookings = relationship("Booking", back_populates="centre_test")
