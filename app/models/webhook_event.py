import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from app.core.database import Base


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String(100), unique=True, index=True, nullable=False)
    event_type = Column(String(100), nullable=False)
    booking_id = Column(String(36), nullable=True, index=True)
    status = Column(String(50), default="PROCESSED", nullable=False)
    payload = Column(Text, nullable=False)
    error_message = Column(Text, nullable=True)
    processed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
