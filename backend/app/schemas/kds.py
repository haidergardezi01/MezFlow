from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict


class KDSModifierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    option_name: str
    price_delta: Decimal


class KDSItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_id: Optional[UUID] = None
    item_name: str
    kitchen_station: str
    quantity: int
    special_instructions: Optional[str] = None
    status: str
    modifiers: List[KDSModifierResponse] = []
    prepared_at: Optional[datetime] = None


class KDSOrderCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    restaurant_id: UUID
    table_id: UUID
    table_number: int
    table_name: Optional[str] = None
    order_number: int
    display_number: str
    status: str
    placed_at: datetime
    confirmed_at: Optional[datetime] = None
    preparing_started_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    dispatched_at: Optional[datetime] = None
    target_prep_minutes: Optional[int] = 15
    elapsed_seconds: int
    urgency_level: str  # NORMAL, WARNING, DELAYED
    notes: Optional[str] = None
    placed_by_diner_name: Optional[str] = None
    items: List[KDSItemResponse]


class KDSSummaryResponse(BaseModel):
    total_active: int
    new: int
    preparing: int
    ready: int
    delayed: int
    by_station: Dict[str, int]


class BumpOrderRequest(BaseModel):
    target_status: Optional[str] = None


class ItemStatusUpdateRequest(BaseModel):
    status: str  # PENDING, PREPARING, READY


class RecallOrderRequest(BaseModel):
    reason: Optional[str] = None
