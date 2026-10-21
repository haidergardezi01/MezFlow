import enum
from sqlalchemy import Column, String, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class TableStatus(str, enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    AWAITING_CLEANUP = "awaiting_cleanup"


class Table(BaseModel):
    __tablename__ = "tables"

    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    table_number = Column(Integer, nullable=False)
    name = Column(String(50), nullable=True)  # e.g. "Table 4" or "Patio 1"
    qr_code_token = Column(String(100), unique=True, nullable=False, index=True)
    capacity = Column(Integer, default=4, nullable=False)
    status = Column(SQLEnum(TableStatus), default=TableStatus.AVAILABLE, nullable=False, index=True)

    # Relationship
    restaurant = relationship("Restaurant", back_populates="tables")
