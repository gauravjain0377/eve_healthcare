from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field


class CentreBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    address: str = Field(..., min_length=5, max_length=500)
    city: str = Field(..., min_length=2, max_length=100)
    contact_phone: Optional[str] = Field(None, max_length=50)


class CentreCreate(CentreBase):
    pass


class CentreUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    address: Optional[str] = None
    city: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: Optional[bool] = None


class CentreTestAssociation(BaseModel):
    test_id: str
    price: Decimal = Field(..., gt=0, decimal_places=2, description="Price of the test at this centre")
    turnaround_hours: int = Field(24, ge=1, le=720, description="Estimated turnaround time in hours")
    is_available: bool = True


class CentreTestResponse(BaseModel):
    centre_test_id: str
    test_id: str
    name: str
    code: str
    category: str
    price: Decimal
    turnaround_hours: int
    is_available: bool

    model_config = {"from_attributes": True}


class CentreResponse(CentreBase):
    id: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CentreDetailResponse(CentreResponse):
    available_tests: List[CentreTestResponse] = []
