from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class OrderSubmitRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=500, description="Optional overall order notes for kitchen")


class OrderItemModifierResponse(BaseModel):
    id: UUID
    modifier_option_id: Optional[UUID] = None
    option_name: str
    price_delta: Decimal
    model_config = ConfigDict(from_attributes=True)


class OrderItemResponse(BaseModel):
    id: UUID
    item_id: Optional[UUID] = None
    diner_id: Optional[UUID] = None
    diner_name: Optional[str] = None
    item_name: str
    kitchen_station: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    special_instructions: Optional[str] = None
    status: str
    modifiers: List[OrderItemModifierResponse] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: UUID
    restaurant_id: UUID
    table_id: UUID
    table_number: int
    session_id: Optional[UUID] = None
    order_number: int
    display_number: str
    status: str
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    placed_by_diner_name: Optional[str] = None
    notes: Optional[str] = None
    placed_at: datetime
    items: List[OrderItemResponse] = []
    currency: str = "PKR"
    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="NEW, CONFIRMED, PREPARING, READY, DISPATCHED, CANCELLED")
