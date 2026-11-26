from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import BaseModel


class PendingRegistration(BaseModel):
    """A restaurant sign-up waiting for its e-mailed code; nothing is created until the code is verified."""
    __tablename__ = "pending_registrations"

    email = Column(String(255), unique=True, nullable=False, index=True)
    payload = Column(JSONB, nullable=False)  # restaurant / manager form fields, never the password
    password_hash = Column(String(255), nullable=False)
    code_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    last_sent_at = Column(DateTime(timezone=True), nullable=False)
