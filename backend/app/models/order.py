import enum
from sqlalchemy import (
    Column,
    String,
    Numeric,
    Integer,
    ForeignKey,
    Text,
    DateTime,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel, get_utc_now


class OrderStatus(str, enum.Enum):
    NEW = "NEW"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    READY = "READY"
    DISPATCHED = "DISPATCHED"
    CANCELLED = "CANCELLED"


class Order(BaseModel):
    __tablename__ = "orders"

    restaurant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    table_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("table_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    order_number = Column(Integer, nullable=False, index=True)
    display_number = Column(String(20), nullable=False, index=True)
    status = Column(
        SQLEnum(OrderStatus),
        default=OrderStatus.NEW,
        nullable=False,
        index=True,
    )
    subtotal = Column(Numeric(10, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    placed_by_diner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("diners.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes = Column(Text, nullable=True)
    placed_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    # Relationships
    restaurant = relationship("Restaurant")
    table = relationship("Table")
    session = relationship("TableSession", back_populates="orders")
    placed_by = relationship("Diner")
    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItem.created_at",
    )


class OrderItem(BaseModel):
    __tablename__ = "order_items"

    order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("menu_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    diner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("diners.id", ondelete="SET NULL"),
        nullable=True,
    )
    item_name = Column(String(150), nullable=False)
    kitchen_station = Column(String(50), default="hot_kitchen", nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    special_instructions = Column(String(255), nullable=True)
    status = Column(String(30), default="PENDING", nullable=False)

    # Relationships
    order = relationship("Order", back_populates="items")
    diner = relationship("Diner")
    modifiers = relationship(
        "OrderItemModifier",
        back_populates="order_item",
        cascade="all, delete-orphan",
    )


class OrderItemModifier(BaseModel):
    __tablename__ = "order_item_modifiers"

    order_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    modifier_option_id = Column(
        UUID(as_uuid=True),
        ForeignKey("modifier_options.id", ondelete="SET NULL"),
        nullable=True,
    )
    option_name = Column(String(100), nullable=False)
    price_delta = Column(Numeric(10, 2), default=0.00, nullable=False)

    # Relationships
    order_item = relationship("OrderItem", back_populates="modifiers")
