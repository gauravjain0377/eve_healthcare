from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TestBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    category: str = Field("GENERAL", max_length=100)


class TestCreate(TestBase):
    pass


class TestUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None


class TestResponse(TestBase):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}
