from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class TableBase(BaseModel):
    table_number: int = Field(..., ge=1)
    name: Optional[str] = Field(None, max_length=50)
    capacity: int = Field(default=4, ge=1, le=50)
    status: str = Field(default="available")


class TableCreate(TableBase):
    pass


class TableUpdate(BaseModel):
    table_number: Optional[int] = Field(None, ge=1)
    name: Optional[str] = Field(None, max_length=50)
    capacity: Optional[int] = Field(None, ge=1, le=50)
    status: Optional[str] = None


class TableResponse(TableBase):
    id: UUID
    restaurant_id: UUID
    qr_code_token: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TableLookupResponse(BaseModel):
    table_id: UUID
    table_number: int
    table_name: Optional[str] = None
    capacity: int
    status: str
    restaurant_id: UUID
    restaurant_name: str
    restaurant_slug: str
    currency: str
    qr_code_token: str


class TableQRGraphicResponse(BaseModel):
    table_id: UUID
    table_number: int
    table_name: Optional[str] = None
    qr_code_token: str
    diner_url: str
    svg_data: str
    png_data_url: str
