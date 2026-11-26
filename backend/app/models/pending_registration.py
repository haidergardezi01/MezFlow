from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
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


class PasswordResetCode(BaseModel):
    """Forgot-password code, stored only as an HMAC; single use, short-lived, limited guesses."""
    __tablename__ = "password_reset_codes"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    code_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
