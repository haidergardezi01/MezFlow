from sqlalchemy import Column, String, Text, Numeric, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class MenuCategory(BaseModel):
    __tablename__ = "menu_categories"

    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    name_ur = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    description_ur = Column(Text, nullable=True)
    icon_name = Column(String(50), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    restaurant = relationship("Restaurant", back_populates="categories")
    items = relationship(
        "MenuItem",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="MenuItem.sort_order",
    )


class MenuItem(BaseModel):
    __tablename__ = "menu_items"

    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("menu_categories.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    name_ur = Column(String(150), nullable=True)
    description = Column(Text, nullable=True)
    description_ur = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    image_url = Column(String(500), nullable=True)
    is_available = Column(Boolean, default=True, nullable=False)
    expected_prep_minutes = Column(Integer, default=15, nullable=False)
    kitchen_station = Column(String(50), default="hot_kitchen", nullable=False)  # grill, fry, hot_kitchen, beverage
    dietary_tags = Column(JSON, nullable=True, default=list)  # e.g. ["halal", "spicy", "vegetarian"]
    sort_order = Column(Integer, default=0, nullable=False)

    # Structured metadata for M7 Grounded AI Dish Explanation:
    # { "heat_level": "medium", "flavor": "savory & spicy", "texture": "tender", "portion_size": "serves 2", "ingredients": ["chicken", "tomatoes", "green chilies", "ginger"] }
    structured_attributes = Column(JSON, nullable=True)

    # Relationships
    restaurant = relationship("Restaurant", back_populates="menu_items")
    category = relationship("MenuCategory", back_populates="items")
    modifier_groups = relationship(
        "ItemModifierGroup",
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="ItemModifierGroup.sort_order",
    )


class ItemModifierGroup(BaseModel):
    __tablename__ = "item_modifier_groups"

    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(UUID(as_uuid=True), ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # e.g., "Spice Level", "Portion Size", "Add-ons"
    name_ur = Column(String(100), nullable=True)
    selection_type = Column(String(20), default="single", nullable=False)  # "single" or "multiple"
    min_selections = Column(Integer, default=0, nullable=False)  # 0 = optional, 1 = required
    max_selections = Column(Integer, default=1, nullable=False)  # 1 = single choice, >1 = multiple
    is_required = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    # Relationships
    item = relationship("MenuItem", back_populates="modifier_groups")
    options = relationship(
        "ModifierOption",
        back_populates="group",
        cascade="all, delete-orphan",
        order_by="ModifierOption.sort_order",
    )
    restaurant = relationship("Restaurant")


class ModifierOption(BaseModel):
    __tablename__ = "modifier_options"

    group_id = Column(UUID(as_uuid=True), ForeignKey("item_modifier_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # e.g., "Mild", "Extra Cheese", "No Onions"
    name_ur = Column(String(100), nullable=True)
    price_delta = Column(Numeric(10, 2), default=0.00, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    # Relationships
    group = relationship("ItemModifierGroup", back_populates="options")
