import enum
from sqlalchemy import (
    Column,
    String,
    Numeric,
    Integer,
    Boolean,
    ForeignKey,
    DateTime,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel, get_utc_now


class SessionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUBMITTING = "SUBMITTING"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"


class TableSession(BaseModel):
    __tablename__ = "table_sessions"

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
    session_token = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(
        SQLEnum(SessionStatus),
        default=SessionStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    host_diner_id = Column(UUID(as_uuid=True), nullable=True)
    total_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    opened_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    restaurant = relationship("Restaurant")
    table = relationship("Table")
    diners = relationship(
        "Diner",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Diner.joined_at",
    )
    cart_items = relationship(
        "CartItem",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="CartItem.created_at",
    )
    orders = relationship("Order", back_populates="session")


class Diner(BaseModel):
    __tablename__ = "diners"

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("table_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    display_name = Column(String(50), nullable=False)
    avatar_color = Column(String(20), default="#F59E0B", nullable=False)
    client_session_id = Column(String(100), nullable=False, index=True)
    is_host = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    joined_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    last_seen_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    # Relationships
    session = relationship("TableSession", back_populates="diners")
    cart_items = relationship("CartItem", back_populates="diner")


class CartItem(BaseModel):
    __tablename__ = "cart_items"

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("table_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("menu_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    diner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("diners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity = Column(Integer, default=1, nullable=False)
    special_instructions = Column(String(255), nullable=True)

    # Relationships
    session = relationship("TableSession", back_populates="cart_items")
    item = relationship("MenuItem")
    diner = relationship("Diner", back_populates="cart_items")
    modifiers = relationship(
        "CartItemModifier",
        back_populates="cart_item",
        cascade="all, delete-orphan",
    )


class CartItemModifier(BaseModel):
    __tablename__ = "cart_item_modifiers"

    cart_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cart_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    modifier_option_id = Column(
        UUID(as_uuid=True),
        ForeignKey("modifier_options.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    option_name_cached = Column(String(100), nullable=True)
    price_delta_cached = Column(Numeric(10, 2), default=0.00, nullable=False)

    # Relationships
    cart_item = relationship("CartItem", back_populates="modifiers")
    modifier_option = relationship("ModifierOption")
