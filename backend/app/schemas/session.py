from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


# -----------------------------------------------------------------------------
# Diner Schemas
# -----------------------------------------------------------------------------
class JoinSessionRequest(BaseModel):
    qr_code_token: str = Field(..., description="Cryptographic QR token of the physical table")
    display_name: str = Field(..., min_length=1, max_length=50, description="Diner display name (e.g. Khizar)")
    client_session_id: Optional[str] = Field(None, description="Persistent client UUID from localStorage/cookie")
    avatar_color: Optional[str] = Field(None, max_length=20, description="Hex color token e.g. #F59E0B")


class DinerResponse(BaseModel):
    id: UUID
    session_id: UUID
    user_id: Optional[UUID] = None
    display_name: str
    avatar_color: str
    client_session_id: str
    is_host: bool
    is_active: bool
    joined_at: datetime
    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Shared Cart Schemas
# -----------------------------------------------------------------------------
class CartItemModifierResponse(BaseModel):
    id: UUID
    modifier_option_id: UUID
    option_name: str
    price_delta: Decimal
    model_config = ConfigDict(from_attributes=True)


class CartItemResponse(BaseModel):
    id: UUID
    session_id: UUID
    item_id: UUID
    item_name: str
    item_name_ur: Optional[str] = None
    base_price: Decimal
    diner_id: UUID
    diner_name: str
    avatar_color: str
    quantity: int
    special_instructions: Optional[str] = None
    modifiers: List[CartItemModifierResponse] = []
    unit_price: Decimal
    line_total: Decimal
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CartResponse(BaseModel):
    session_id: UUID
    restaurant_id: UUID
    table_id: UUID
    table_number: int
    status: str
    items: List[CartItemResponse] = []
    diners: List[DinerResponse] = []
    subtotal: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    total_amount: Decimal = Decimal("0.00")
    currency: str = "PKR"
    item_count: int = 0


class CartItemCreate(BaseModel):
    item_id: UUID
    quantity: int = Field(default=1, ge=1, le=50)
    selected_modifier_option_ids: List[UUID] = Field(default_factory=list)
    special_instructions: Optional[str] = Field(None, max_length=255)


class CartItemUpdate(BaseModel):
    quantity: Optional[int] = Field(None, ge=0, le=50)
    special_instructions: Optional[str] = Field(None, max_length=255)


# -----------------------------------------------------------------------------
# Table Session Schemas
# -----------------------------------------------------------------------------
class TableSessionResponse(BaseModel):
    id: UUID
    restaurant_id: UUID
    table_id: UUID
    table_number: int
    session_token: str
    status: str
    host_diner_id: Optional[UUID] = None
    opened_at: datetime
    total_amount: Decimal
    current_diner: Optional[DinerResponse] = None
    diners: List[DinerResponse] = []
    cart: Optional[CartResponse] = None
    model_config = ConfigDict(from_attributes=True)
