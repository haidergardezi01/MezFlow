from sqlalchemy import Column, String, Text, Numeric, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class MenuCategory(BaseModel):
    __tablename__ = "menu_categories"

    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    restaurant = relationship("Restaurant", back_populates="categories")
    items = relationship("MenuItem", back_populates="category", cascade="all, delete-orphan")


class MenuItem(BaseModel):
    __tablename__ = "menu_items"

    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("menu_categories.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    image_url = Column(String(500), nullable=True)
    is_available = Column(Boolean, default=True, nullable=False)
    expected_prep_minutes = Column(Integer, default=15, nullable=False)
    kitchen_station = Column(String(50), default="hot_kitchen", nullable=False)  # grill, fry, hot_kitchen, beverage

    # Structured metadata for M7 Grounded AI Dish Explanation:
    # { "heat_level": "medium", "flavor": "savory & spicy", "texture": "tender", "portion_size": "serves 2", "ingredients": ["chicken", "tomatoes", "green chilies", "ginger"] }
    structured_attributes = Column(JSON, nullable=True)

    # Relationships
    restaurant = relationship("Restaurant", back_populates="menu_items")
    category = relationship("MenuCategory", back_populates="items")
