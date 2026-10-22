from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


# -----------------------------------------------------------------------------
# Modifier Option Schemas
# -----------------------------------------------------------------------------
class ModifierOptionBase(BaseModel):
    name: str = Field(..., max_length=100)
    name_ur: Optional[str] = Field(None, max_length=100)
    price_delta: Decimal = Field(default=Decimal("0.00"), ge=Decimal("-100000.00"), le=Decimal("100000.00"))
    is_default: bool = False
    is_available: bool = True
    sort_order: int = 0


class ModifierOptionCreate(ModifierOptionBase):
    pass


class ModifierOptionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    name_ur: Optional[str] = Field(None, max_length=100)
    price_delta: Optional[Decimal] = None
    is_default: Optional[bool] = None
    is_available: Optional[bool] = None
    sort_order: Optional[int] = None


class ModifierOptionResponse(ModifierOptionBase):
    id: UUID
    group_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Item Modifier Group Schemas
# -----------------------------------------------------------------------------
class ModifierGroupBase(BaseModel):
    name: str = Field(..., max_length=100)
    name_ur: Optional[str] = Field(None, max_length=100)
    selection_type: str = Field(default="single", description="'single' or 'multiple'")
    min_selections: int = Field(default=0, ge=0)
    max_selections: int = Field(default=1, ge=1)
    is_required: bool = False
    sort_order: int = 0


class ModifierGroupCreate(ModifierGroupBase):
    pass


class ModifierGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    name_ur: Optional[str] = Field(None, max_length=100)
    selection_type: Optional[str] = None
    min_selections: Optional[int] = None
    max_selections: Optional[int] = None
    is_required: Optional[bool] = None
    sort_order: Optional[int] = None


class ModifierGroupResponse(ModifierGroupBase):
    id: UUID
    restaurant_id: UUID
    item_id: UUID
    options: List[ModifierOptionResponse] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Menu Item Schemas
# -----------------------------------------------------------------------------
class MenuItemBase(BaseModel):
    name: str = Field(..., max_length=150)
    name_ur: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = None
    description_ur: Optional[str] = None
    price: Decimal = Field(..., ge=Decimal("0.00"))
    image_url: Optional[str] = Field(None, max_length=500)
    is_available: bool = True
    expected_prep_minutes: int = Field(default=15, ge=1)
    kitchen_station: str = Field(default="hot_kitchen", max_length=50)
    dietary_tags: Optional[List[str]] = Field(default_factory=list)
    sort_order: int = 0
    structured_attributes: Optional[Dict[str, Any]] = None


class MenuItemCreate(MenuItemBase):
    category_id: UUID


class MenuItemUpdate(BaseModel):
    category_id: Optional[UUID] = None
    name: Optional[str] = Field(None, max_length=150)
    name_ur: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = None
    description_ur: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=Decimal("0.00"))
    image_url: Optional[str] = Field(None, max_length=500)
    is_available: Optional[bool] = None
    expected_prep_minutes: Optional[int] = Field(None, ge=1)
    kitchen_station: Optional[str] = Field(None, max_length=50)
    dietary_tags: Optional[List[str]] = None
    sort_order: Optional[int] = None
    structured_attributes: Optional[Dict[str, Any]] = None


class MenuItemResponse(MenuItemBase):
    id: UUID
    restaurant_id: UUID
    category_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MenuItemDetailResponse(MenuItemResponse):
    modifier_groups: List[ModifierGroupResponse] = []


# -----------------------------------------------------------------------------
# Menu Category Schemas
# -----------------------------------------------------------------------------
class MenuCategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    name_ur: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    description_ur: Optional[str] = None
    icon_name: Optional[str] = Field(None, max_length=50)
    sort_order: int = 0
    is_active: bool = True


class MenuCategoryCreate(MenuCategoryBase):
    pass


class MenuCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    name_ur: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    description_ur: Optional[str] = None
    icon_name: Optional[str] = Field(None, max_length=50)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class MenuCategoryResponse(MenuCategoryBase):
    id: UUID
    restaurant_id: UUID
    items: List[MenuItemDetailResponse] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Public Catalog & Real-Time Payloads
# -----------------------------------------------------------------------------
class PublicMenuResponse(BaseModel):
    restaurant_id: UUID
    restaurant_name: str
    currency: str = "PKR"
    categories: List[MenuCategoryResponse]


class AvailabilityToggleRequest(BaseModel):
    is_available: bool


class MenuRealtimeEvent(BaseModel):
    event: str  # "ITEM_AVAILABILITY_CHANGED", "MENU_ITEM_UPDATED", "CATEGORY_UPDATED"
    item_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    is_available: Optional[bool] = None
    price: Optional[Decimal] = None
    name: Optional[str] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
