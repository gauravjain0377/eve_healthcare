from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
from app.models.booking import BookingStatus


class BookingCreate(BaseModel):
    centre_id: str = Field(..., description="ID of the diagnostic centre")
    test_id: str = Field(..., description="ID of the diagnostic test to book")
    appointment_time: datetime = Field(..., description="Desired appointment date and time (ISO format)")
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("appointment_time")
    @classmethod
    def validate_future_date(cls, v: datetime) -> datetime:
        # Normalize timezone to compare safely
        now = datetime.now(timezone.utc)
        if v.tzinfo is None:
            v_cmp = v.replace(tzinfo=timezone.utc)
        else:
            v_cmp = v
        if v_cmp <= now:
            raise ValueError("Appointment time must be in the future.")
        return v


class BookingResponse(BaseModel):
    id: str
    user_id: str
    centre_id: str
    test_id: str
    appointment_time: datetime
    amount: Decimal
    status: BookingStatus
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BookingDetailResponse(BookingResponse):
    centre_name: Optional[str] = None
    centre_city: Optional[str] = None
    test_name: Optional[str] = None
    test_code: Optional[str] = None
    patient_name: Optional[str] = None
    patient_email: Optional[str] = None


class BookingStatusUpdate(BaseModel):
    status: BookingStatus
