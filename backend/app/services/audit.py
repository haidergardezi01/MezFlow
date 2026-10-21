from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog


async def record_audit_log(
    db: AsyncSession,
    restaurant_id: UUID,
    action: str,
    user_id: Optional[UUID] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """
    Appends an immutable audit log entry into the database.
    (Satisfies FR-M1-06 and NFR-10).
    """
    log_entry = AuditLog(
        restaurant_id=restaurant_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
    )
    db.add(log_entry)
    await db.flush()
    return log_entry
